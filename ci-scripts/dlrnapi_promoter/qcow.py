"""
This file contains classes and functionto interact with qcow images servers
"""
import logging
import os
import subprocess
import sys


class QcowClient(object):
    """
    This class interacts with qcow images servers
    """
    log = logging.getLogger("promoter")

    def __init__(self, config):
        self.config = config
        relpath = "ci-scripts/dlrnapi_promoter"
        script_root = os.path.abspath(sys.path[0]).replace(relpath, "")
        self.promote_script = script_root + 'ci-scripts/promote-images.sh'

    def promote_images(self, candidate_hash, target_label):
        """
        This method promotes images contained inside a dir in the server
        whose name is equal to the dlrn_id specified by creating a
        symlink to it named as the target_label
        :param candidate_hash:  The hash object to select images dir
        :param target_label: The name of the symlink
        :return: None
        """
        try:
            self.log.info(
                'Promoting the qcow image for dlrn hash %s on %s to %s',
                candidate_hash.full_hash, self.config.release, target_label)
            # The script doesn't really use commit/distro or full hash,
            # it just needs the hash to identify the dir, so it works with
            # either dlrnhash or aggregated hash.
            qcow_logs = subprocess.check_output(
                ['bash', self.promote_script,
                 '--distro', self.config.distro_name,
                 '--distro-version', self.config.distro_version,
                 self.config.release, candidate_hash.full_hash,
                 target_label],
                stderr=subprocess.STDOUT).split("\n")
            for line in qcow_logs:
                self.log.info(line)
        except subprocess.CalledProcessError as ex:
            self.log.error('QCOW IMAGE UPLOAD FAILED LOGS BELOW:')
            self.log.error(ex.output)
            self.log.exception(ex)
            self.log.error('END OF QCOW IMAGE UPLOAD FAILURE')
            raise
