"""
This file contains classes and functionto interact with qcow images servers
"""
import copy
import logging
import os
import paramiko
import subprocess

from common import PromotionError


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

        # Try to load experimental config
        if hasattr(config, 'qcow_server'):
            server_conf = self.config.qcow_server
            self.user = server_conf['user']
            self.root = server_conf['root']
            self.host = server_conf['host']
            if self.host == "localhost":
                self.user = None

            self.images_dir = os.path.join(self.root, config.distro,
                                           config.release, "rdo_trunk")

            client = paramiko.SSHClient()
            client.load_system_host_keys()

            client.connect(self.host, username=self.user)
            self.client = client.open_sftp()

    def promote_experimental(self, dlrn_hash, name, create_previous=False):
        try:
            current_hash = self.client.readlink(name)
        except IOError:
            pass

        self.client.symlink(dlrn_hash.full_hash, name)

    def get_previous_hash(self, promote_name):
        try:
            image_dir = self.client.readlink("previous" + promote_name)
        except IOError:
            pass
        previous_hash = image_dir

        return previous_hash

    def promote(self, candidate_hash, target_label, **kwargs):
        """
        This method promotes images contained inside a dir in the server
        whose name is equal to the dlrn_id specified by creating a
        symlink to it named as the target_label.
        It currently uses an external Bash script for the effective promotion
        :param candidate_hash:  The hash object to select images dir
        :param target_label: The name of the symlink
        :return: None
        """
        try:
            self.log.info("Qcow promote '{}' to {}: Attempting promotion"
                          "".format(candidate_hash, target_label))
            # The script doesn't really use commit/distro or full hash,
            # it just needs the hash to identify the dir, so it works with
            # either dlrnhash or aggregated hash.
            cmd = ['bash',
                   self.promote_script,
                   '--distro', self.config.distro_name,
                   '--distro-version', self.config.distro_version,
                   self.config.release,
                   candidate_hash.full_hash,
                   target_label
                   ]
            qcow_logs = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            qcow_logs_lines = qcow_logs.decode("UTF-8").split("\n")
            self.log.info("Qcow promote '{}' to {}: Successful promotion"
                          "".format(candidate_hash, target_label))
            self.log.info("Qcow promote '{}' to {}: Successful promotion "
                          "start logs -----------------------------"
                          "".format(candidate_hash, target_label))
            for line in qcow_logs_lines:
                self.log.info(line)
            self.log.info("Qcow promote '{}' to {}: Successful promotion "
                          "end logs -----------------------------"
                          "".format(candidate_hash, target_label))
        except subprocess.CalledProcessError as ex:
            self.log.error("Qcow promote '{}' to {}: Failed promotion"
                           "".format(candidate_hash, target_label))
            self.log.error("Qcow promote '{}' to {}: Failed promotion start "
                           "logs -----------------------------"
                           "".format(candidate_hash, target_label))
            for line in ex.output.decode("UTF-8").split("\n"):
                self.log.error(line)
            self.log.exception(ex)
            self.log.error("Qcow promote '{}' to {}: Failed promotion end "
                           "logs -----------------------------"
                           "".format(candidate_hash, target_label))
            raise PromotionError("Failed to promote overcloud images")

# ###-------- The code that follows is experimental and untested

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
        :return:
        """

        results = {
            "hash_valid": False,
            "promotion_valid": False,
            "qcow_valid": False,
            "missing_qcows": copy.copy(self.config.qcow_images),
            "present_qcows": [],
        }
        if assume_valid:
            results = {
                "hash_valid": True,
                "promotion_valid": True,
                "qcow_valid": True,
                "present_qcows": copy.copy(self.config.qcow_images),
                "missing_qcows": [],
            }
            return results

        try:
            images_path = os.path.join(self.images_dir, dlrn_hash.full_hash)
            stat = self.client.stat(images_path)
            results['hash_valid'] = True
            images = sorted(self.client.listdir(images_path))
            results['present_qcows'] = images
            results['missing_qcows'] = \
                list(set(self.config.qcow_images).difference(images))
            if images == self.config.qcow_images:
                results['qcow_valid'] = True
        except IOError:
            pass

        if name is not None:
            try:
                link = self.client.readlink(name)
                if link == dlrn_hash.full_hash:
                    results['promotion_valid'] = True
            except IOError:
                pass

        return results
