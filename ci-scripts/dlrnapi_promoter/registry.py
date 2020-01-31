"""
This file contains classes and functionto interact with containers registries
"""
import datetime
import logging
import os
import pprint
import re
import subprocess

from common import PromotionError


class RegistriesClient(object):
    """
    This class interacts with containers registries
    """

    log = logging.getLogger("promoter")

    def __init__(self, config):
        self.config = config
        self.git_root = self.config.git_root
        self.logfile = os.path.abspath(os.path.join(
            self.git_root,
            "../promoter_logs/container-push/%s.log" %
            datetime.datetime.now().strftime("%Y%m%d-%H%M%S")))
        self.promote_playbook = os.path.join(self.git_root,
                                             'ci-scripts',
                                             'container-push',
                                             'container-push.yml')
        self.push_opts = ("-e manifest_push=%s -e target_registries_push=%s"
                          "" % (self.config.manifest_push,
                                self.config.target_registries_push))

        env = os.environ
        env['RELEASE'] = self.config.release
        env['SCRIPT_ROOT'] = self.git_root
        env['DISTRO_NAME'] = self.config.distro_name
        env['DISTRO_VERSION'] = self.config.distro_version
        self.promote_env = env

    def promote(self, candidate_hash, target_label, **kwargs):
        """
        This method promotes containers whose tag is equal to the dlrn_id
        specified by retagging them with the target_label.
        Currently invokes an external ansible playbook for the effective
        promotion
        :param candidate_hash:  The hash to select container tags
        :param target_label: the new tag to apply to the containers
        :param kwarg: unused
        :return: None
        """

        self.log.info("Containers promote '{}' to {}: Attempting promotion"
                      "".format(candidate_hash, target_label))

        self.promote_env['PROMOTE_NAME'] = target_label
        self.promote_env['COMMIT_HASH'] = candidate_hash.commit_hash
        self.promote_env['DISTRO_HASH'] = candidate_hash.distro_hash
        self.promote_env['FULL_HASH'] = candidate_hash.full_hash
        # Use single string to make it easy to copy/paste from logs
        cmd = (
            "env "
            "ANSIBLE_LOG_PATH=%s"
            "RELEASE=%s "
            "COMMIT_HASH=%s "
            "DISTRO_HASH=%s "
            "FULL_HASH=%s "
            "PROMOTE_NAME=%s "
            "SCRIPT_ROOT=%s "
            "DISTRO_NAME=%s "
            "DISTRO_VERSION=%s "
            "ANSIBLE_DEBUG=False "
            "ansible-playbook -v %s %s" % (
                self.logfile,
                self.config.release,
                candidate_hash.commit_hash,
                candidate_hash.distro_hash,
                candidate_hash.full_hash,
                target_label,
                self.git_root,
                self.config.distro_name,
                self.config.distro_version,
                self.push_opts,
                self.promote_playbook
            )
        )
        # Remove color codes from ansible output
        ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
        try:
            self.log.info('Running: %s', cmd)
            container_logs = subprocess.check_output(cmd.split(" "),
                                                     stderr=subprocess.STDOUT)
            # containers_log needs decoding in python3
            if type(container_logs) is not str:
                container_logs = container_logs.decode()
            self.log.info("Containers promote '{}' to {}: Successful promotion"
                          "".format(candidate_hash, target_label))
            self.log.info("Containers promote '{}' to {}: Successful promotion "
                          "start logs -----------------------------"
                          "".format(candidate_hash, target_label))
            # for line in container_logs.split("\n"):
            #     self.log.info(ansi_escape.sub('', line))
            self.log.info("Containers promote '{}' to {}: Successful promotion "
                          "end logs -----------------------------"
                          "".format(candidate_hash, target_label))
        except subprocess.CalledProcessError as ex:
            self.log.error("Containers promote '{}' to {}: Failed promotion"
                           "".format(candidate_hash, target_label))
            self.log.error("Containers promote '{}' to {}: Failed promotion"
                           "start logs -----------------------------"
                           "".format(candidate_hash, target_label))
            for line in ex.output.decode("UTF-8").split("\n"):
                self.log.error(ansi_escape.sub('', line))
            self.log.exception(ex)
            self.log.error("Containers promote '{}' to {}: Failed promotion end"
                           " logs -----------------------------"
                           "".format(candidate_hash, target_label))
            raise PromotionError("Failed to promote overcloud images")
