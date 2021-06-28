"""
This file contains classes and functionto interact with qcow images servers
to upload dockerfiles
"""
import logging
import os

import paramiko
from common import PromotionError


class DockerfileConnectionClient(object):
    """
    Proxy class for client connection
    """

    _log = logging.getLogger("promoter")

    def __init__(self, server_conf):
        self._host = server_conf['host']
        self._user = server_conf['user']
        self._client_type = server_conf['client']
        self._keypath = server_conf['keypath']
        self._client = os
        if self._client_type == "sftp":
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            keypath = os.path.expanduser(self._keypath)
            self.key = paramiko.RSAKey.from_private_key_file(filename=keypath)
            self.kwargs = {}
            if self._user is not None:
                self.kwargs['username'] = self._user
            else:
                self.kwargs['username'] = os.environ.get("USER")

            self._log.debug("Connecting to %s as user %s", self._host,
                            self._user)

            self.ssh_client = client

    def connect(self):
        if hasattr(self, 'ssh_client'):
            self.ssh_client.connect(self._host, pkey=self.key, **self.kwargs)
            self._client = self.ssh_client.open_sftp()

    def __getattr__(self, item):
        return getattr(self._client, item)

    def close(self):
        if self._client_type == "sftp":
            self._client.close()


class DockerfileClient(object):
    """
    This class interacts with qcow images servers
    """
    log = logging.getLogger("promoter")

    def __init__(self, config):
        self.config = config
        self.release = config.release
        self.git_root = self.config.git_root
        self.distro_name = self.config.distro_name
        self.distro_version = self.config.distro_version
        self.rollback_links = {}
        server_conf = self.config.overcloud_images.get('qcow_servers')
        qcow_server = self.config.default_qcow_server
        self.user = server_conf[qcow_server]['user']
        self.root = self.config.dockerfile_root
        self.host = server_conf[qcow_server]['host']
        downstream_release_map = {'osp16-2': 'rhos-16.2',
                                  'osp17': 'rhos-17'}
        if self.config.release.startswith('osp'):
            self.release = downstream_release_map[self.release]

        self.client = DockerfileConnectionClient(server_conf[qcow_server])
        self.images_dir = os.path.join(
            os.path.join(config.stage_root, self.root),
            config.distro, self.release, "rdo_trunk")
        if self.config.release.startswith('osp'):
            self.images_dir = self.images_dir.rstrip("/rdo_trunk")

    def promote(self, candidate_hash, target_label, candidate_label=None,
                create_previous=True):
        """
        Effective promotion of the dockerfiles. This method will handle symbolic
        links to the dir containing dockerfiles from the candidate hash,
        optionally saving the current link as previous
        :param candidate_hash: The dlrn hash to promote
        :param target_label: The name of the link to create
        :param candidate_label: Currently unused
        :param create_previous: A bool to determine if previous link is created
        :return: None
        """

        self.client.connect()

        self.client.chdir(self.images_dir)
        self.log.debug("Changing dir: {}".format(self.images_dir))
        log_header = "Qcow promote '{}' to {}:".format(candidate_hash,
                                                       target_label)
        self.log.info("%s Attempting promotion", log_header)

        # Check if candidate_hash dir is present
        try:
            self.client.stat(candidate_hash.full_hash)
            self.log.debug("Checking candidate hash dir: "
                           "{}".format(candidate_hash.full_hash))
        except EnvironmentError as ex:
            self.log.error("%s images dir for hash %s not present or not "
                           "accessible", log_header, candidate_hash)
            self.log.exception(ex)
            self.client.close()
            raise PromotionError("{} No images dir for hash {}"
                                 "".format(log_header, candidate_hash))

        # Check if the target label exists and points to a hash dir
        current_hash = None
        try:
            current_hash = self.client.readlink(target_label)
            self.log.debug("Checking target link: {}".format(current_hash))
        except EnvironmentError:
            self.log.debug("%s No link named %s exists", log_header,
                           target_label)

        # If this exists Check if we can remove  the symlink
        if current_hash:
            self.rollback_links['target_label'] = current_hash
            try:
                self.client.remove(target_label)
                self.log.debug("Removing label: {}".format(target_label))
            except EnvironmentError as ex:
                self.log.debug("Unable to remove the target_label: %s",
                               target_label)
                self.log.exception(ex)
                self.client.close()
                raise

        # Check if a previous link exists and points to an hash-dir
        previous_label = "previous-{}".format(target_label)
        previous_hash = None
        try:
            previous_hash = self.client.readlink(previous_label)
            self.log.debug("Previous hash: {}".format(previous_hash))
        except EnvironmentError:
            self.log.debug("%s No previous-link named %s exists",
                           log_header,
                           previous_label)
        self.log.debug("Previous hash %s", previous_hash)
        # If it exists and we are handling it, check if we can remove and
        # reassign it
        if current_hash and previous_hash and create_previous:
            self.rollback_links[previous_label] = previous_hash
            try:
                self.client.remove(previous_label)
                self.log.debug("Removing previous label: "
                               "{}".format(previous_label))
            except EnvironmentError as ex:
                self.log.debug("Unable to remove the target_label: %s",
                               target_label)
                self.log.exception(ex)
                self.client.close()
                # Rollback is not tested, we enable it later, when tests are
                # easier to add
                # self.rollback()
                raise
            try:
                self.client.symlink(current_hash, previous_label)
                self.log.debug("Created symlink: "
                               "{} -> {}".format(current_hash, previous_label))
            except EnvironmentError as ex:
                self.log.error("%s failed to link %s to %s", log_header,
                               previous_label, current_hash)
                self.log.exception(ex)
                # Rollback is not tested, we enable it later, when tests are
                # easier to add
                # self.rollback()
                self.client.close()
                raise

        # Finally the effective promotion
        try:
            self.client.symlink(candidate_hash.full_hash, target_label)
            self.log.debug("Created symlink {} -> {}".format(
                candidate_hash.full_hash, target_label))
        except EnvironmentError as ex:
            self.log.error("%s failed to link %s to %s", log_header,
                           target_label, candidate_hash.full_hash)
            self.log.exception(ex)
            # Rollback is not tested, we enable it later, when tests are
            # easier to add
            # self.rollback()
        finally:
            self.client.close()

        self.log.info("%s Successful promotion", log_header)
