"""
This file contains classes and functionto interact with containers registries
"""
import datetime
import logging
import os
import pprint
import re
import subprocess
import sys


class RegistriesClient(object):
    """
    This class interacts with containers registries
    """

    log = logging.getLogger("promoter")

    def __init__(self, config):
        self.config = config
        relpath = "ci-scripts/dlrnapi_promoter"
        self.script_root = os.path.abspath(sys.path[0]).replace(relpath, "")
        self.logfile = os.path.abspath(os.path.join(
            self.script_root,
            "../promoter_logs/container-push/%s.log" %
            datetime.datetime.now().strftime("%Y%m%d-%H%M%S")))
        self.promote_playbook = os.path.join(self.script_root,
                                             'ci-scripts/container-push',
                                             'container-push.yml')
        self.push_opts = ("-e manifest_push=%s -e target_registries_push=%s"
                          "" % (self.config.manifest_push,
                                self.config.target_registries_push))

        env = os.environ
        env['RELEASE'] = self.config.release
        env['SCRIPT_ROOT'] = self.script_root
        env['DISTRO_NAME'] = self.config.distro_name
        env['DISTRO_VERSION'] = self.config.distro_version
        self.promote_env = env

    def promote(self, candidate_hash, target_label, **kwargs):
        """
        This method promotes containers whose tag is equal to the dlrn_id
        specified by retagging them with the target_label
        Right now is just a wrapper around legacy code to easily pass config
        information
        :param candidate_hash:  The hash to select container tags
        :param target_label: the new tag to apply to the containers
        :return: None
        """

        self.log.info(
            'Promoting the container images for dlrn hash %s on '
            '%s to %s', candidate_hash.full_hash, self.config.release,
            target_label)

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
            "ansible-playbook %s %s" % (
                self.logfile,
                self.config.release,
                candidate_hash.commit_hash,
                candidate_hash.distro_hash,
                candidate_hash.full_hash,
                target_label,
                self.script_root,
                self.config.distro_name,
                self.config.distro_version,
                self.push_opts,
                self.promote_playbook
            )
        )
        ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
        try:
            self.log.info('Running: %s', cmd)
            container_logs = subprocess.check_output(cmd.split(" "),
                                                     stderr=subprocess.STDOUT)
            # containers_log needs decoding in python3
            if type(container_logs) is not str:
                container_logs = container_logs.decode()
            for line in container_logs.split("\n"):
                self.log.info(ansi_escape.sub('', line))
        except subprocess.CalledProcessError as ex:
            self.log.error('CONTAINER IMAGE UPLOAD FAILED LOGS BELOW:')
            for line in ex.output.decode("UTF-8").split("\n"):
                self.log.error(ansi_escape.sub('', line))
            self.log.exception(ex)
            self.log.error('END OF CONTAINER IMAGE UPLOAD FAILURE')
            raise
