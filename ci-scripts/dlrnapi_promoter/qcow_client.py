"""
This file contains classes and functionto interact with qcow images servers
"""
import copy
import logging
import os
import paramiko

from common import PromotionError

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


class QcowConnectionClient(object):
    """
    Proxy class for client connection
    """

    _log = logging.getLogger("promoter")

    def __init__(self, server_conf):
        self._host = server_conf['host']
        self._user = server_conf['user']
        self._client_type = server_conf['client']
        self._client = os
        if server_conf['client'] == "sftp":
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.WarningPolicy)

            keypath = os.path.expanduser('~/.ssh/id_rsa')
            key = paramiko.rsakey.RSAKey(filename=keypath)
            kwargs = {}
            if self._user is not None:
                kwargs['username'] = self._user
            else:
                kwargs['username'] = os.environ.get("USER")

            self._log.debug("Connecting to %s as user %s", self._host,
                            self._user)
            client.connect(self._host, pkey=key, **kwargs)
            self._client = client.open_sftp()

    def __getattr__(self, item):
        return getattr(self._client, item)

    def close(self):
        if self._client_type == "sftp":
            self._client.close()


class QcowClient(object):
    """
    This class interacts with qcow images servers
    """
    log = logging.getLogger("promoter")

    def __init__(self, config):
        self.config = config

        self.git_root = self.config.git_root
        self.promote_script = os.path.join(self.git_root,
                                           'ci-scripts', 'promote-images.sh')

        self.distro_name = self.config.distro_name
        self.distro_version = self.config.distro_version
        # Try to load experimental config
        # Currently paramiko is not in requirements, and I don't want to
        # add it for the experimental code.
        server_conf = self.config.qcow_server
        self.user = server_conf['user']
        self.root = server_conf['root']
        self.host = server_conf['host']

        self.client = QcowConnectionClient(server_conf)

        self.images_dir = os.path.join(self.root, config.distro,
                                       config.release, "rdo_trunk")

    def validate_qcows(self, dlrn_hash, name=None, assume_valid=False):
        """
        Check we have the images dir in the server
        if name is specified, verify that name points to the hash
        - maybe qcow ran and failed
        Check at which point of qcow promotion we stopped
        1) did we create a new symlink ?
        2) did we create the previous symlink ?
        3) are all the images uploaded correctly ?
        :param dlrn_hash: The hash to check
        :param name: The promotion name
        :param assume_valid: report everything worked unconditionally
        :return: A dict with result of the validation
        """

        try:
            self.client.chdir(self.images_dir)
        except IOError as ex:
            self.log.error("Qcow-client: Image root dir %s does not exist "
                           "in the server")
            self.log.exception(ex)
            raise

        results = {
            "hash_valid": False,
            "promotion_valid": False,
            "qcow_valid": False,
            "missing_qcows": copy.copy(
                self.config.overcloud_images['qcow_images']),
            "present_qcows": [],
        }

        try:
            images_path = os.path.join(self.images_dir, dlrn_hash.full_hash)
            stat = self.client.stat(images_path)
            if stat:
                pass
            results['hash_valid'] = True
            images = sorted(self.client.listdir(images_path))
            results['present_qcows'] = images
            results['missing_qcows'] = \
                list(set(self.config.overcloud_images[
                             'qcow_images']).difference(
                    images))
            if images == self.config.overcloud_images['qcow_images']:
                results['qcow_valid'] = True
        except (FileNotFoundError, IOError):
            pass

        if name is not None:
            try:
                link = self.client.readlink(name)
                if link == dlrn_hash.full_hash:
                    results['promotion_valid'] = True
            except IOError:
                pass

        return results

    def promote(self, candidate_hash, target_label, candidate_label=None,
                create_previous=True,):

        self.validate_qcows(candidate_hash)

        log_header = "Qcow promote '{}' to {}:".format(candidate_hash,
                                                       target_label)
        self.log.info("%s Attempting promotion", log_header)
        try:
            self.client.stat(candidate_hash.full_hash)
        except Exception as ex:
            self.log.error("%s No images dir for hash %s", log_header,
                           candidate_hash)
            self.log.exception(ex)
            self.client.close()
            raise PromotionError("{} No images dir for hash {}"
                                 "".format(log_header, candidate_hash))

        current_hash = None
        try:
            current_hash = self.client.readlink(target_label)
            self.client.remove(target_label)
        except IOError:
            self.log.debug("%s No link named %s exists", log_header,
                           target_label)

        if current_hash and create_previous:
            previous_label = "previous-{}".format(target_label)
            try:
                self.client.remove(previous_label)
            except IOError:
                self.log.debug("%s No previous-link named %s exists",
                               log_header,
                               previous_label)
            try:
                self.client.symlink(current_hash, previous_label)
            except IOError as ex:
                self.log.error("%s failed to link %s to %s", log_header,
                               previous_label, current_hash)
                self.log.exception(ex)
                self.client.close()
                raise

        try:
            self.client.symlink(candidate_hash.full_hash, target_label)
        except IOError as ex:
            self.log.error("%s failed to link %s to %s", log_header,
                           target_label, candidate_hash.full_hash)
            self.log.exception(ex)
        finally:
            self.client.close()

        self.log.info("%s Successful promotion", log_header)

    def get_previous_hash(self, promote_name):
        try:
            image_dir = self.client.readlink("previous" + promote_name)
        except IOError:
            pass
        previous_hash = image_dir

        return previous_hash
