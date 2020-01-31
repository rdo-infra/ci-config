"""
This file contains classes and functionto interact with qcow images servers
"""
import logging
import os
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
