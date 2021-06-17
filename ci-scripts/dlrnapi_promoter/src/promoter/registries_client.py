"""
This file contains classes and functionto interact with containers registries
"""
import datetime
import logging
import os
import re
import subprocess
import tempfile

import yaml
from promoter.common import PromotionError
from promoter.repo_client import RepoClient


class RegistriesClient(object):
    """
    This class interacts with containers registries
    """

    log = logging.getLogger("promoter")

    def __init__(self, config):
        self.config = config
        self.git_root = self.config.git_root
        self.log_root = os.path.expanduser(
            self.config.container_push_logfile)
        self.logfile = os.path.join(
            self.log_root,
            "%s.log" % datetime.datetime.now().strftime(
                "%Y%m%d-%H%M%S"))
        self.promote_playbook = os.path.join(self.git_root,
                                             'ci-scripts',
                                             'container-push',
                                             'container-push.yml')

        self.extra_vars = {
            'release': self.config.release,
            'script_root': self.git_root,
            'distro_name': self.config.distro_name,
            'distro_version': self.config.distro_version,
            'manifest_push': self.config.manifest_push,
            'target_registries_push': self.config.target_registries_push
        }
        self.repo_client = RepoClient(self.config)

    def prepare_extra_vars(self, candidate_hash, target_label, candidate_label):
        versions_reader = self.repo_client.get_versions_csv(candidate_hash,
                                                            candidate_label)
        if versions_reader is None:
            self.log.error("No versions.csv found")
            raise PromotionError

        tripleo_sha = \
            self.repo_client.get_commit_sha(versions_reader,
                                            "openstack-tripleo-common")
        if not tripleo_sha:
            self.log.error("Versions.csv does not contain tripleo-common "
                           "commit")
            raise PromotionError

        containers_dict = self.repo_client.get_containers_list(tripleo_sha)
        ppc_containers_list = containers_dict.get('ppc_containers_list', [])
        x86_containers_list = containers_dict.get('containers_list', [])
        if not x86_containers_list:
            self.log.error("Containers list is empty")
            raise PromotionError

        extra_vars = {
            'candidate_label': candidate_label,
            'named_label': target_label,
            'commit_hash': candidate_hash.commit_hash,
            'distro_hash': candidate_hash.distro_hash,
            'full_hash': candidate_hash.full_hash,
            'containers_list': x86_containers_list,
            'ppc_containers_list': ppc_containers_list,
            'source_namespace': self.config.source_namespace,
            'target_namespace': self.config.target_namespace
        }

        self.extra_vars.update(extra_vars)
        __, extra_vars_path = tempfile.mkstemp(suffix=".yaml")
        self.log.debug("Crated extra vars file at %s", extra_vars_path)
        self.log.info("Passing extra vars to playbook: %s",
                      str(self.extra_vars))
        with open(extra_vars_path, "w") as extra_vars_file:
            yaml.safe_dump(self.extra_vars, extra_vars_file)

        return extra_vars_path

    def promote(self, candidate_hash, target_label, candidate_label=None):
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

        extra_vars_path = self.prepare_extra_vars(candidate_hash,
                                                  target_label, candidate_label)

        log_dir = self.log_root + "/".join(self.logfile.split("/")[:-1])

        logfile = os.path.join(log_dir, self.logfile)
        # Use single string to make it easy to copy/paste from logs
        cmd = (
            "env "
            "ANSIBLE_LOG_PATH={} "
            "ANSIBLE_DEBUG=False "
            "ansible-playbook -v -e @{} {}".format(
                logfile,
                extra_vars_path,
                self.promote_playbook,
            )
        )

        log_header = "Containers promote '{}' to {}:".format(candidate_hash,
                                                             target_label)
        # Remove color codes from ansible output
        ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
        try:
            self.log.info('Running: %s', cmd)
            container_logs = subprocess.check_output(cmd.split(" "),
                                                     stderr=subprocess.STDOUT)
            # containers_log needs decoding in python3
        except subprocess.CalledProcessError as ex:
            os.unlink(extra_vars_path)
            self.log.error("%s Failed promotion", log_header)
            self.log.error("%s Failed promotion"
                           "start logs -----------------------------",
                           log_header)
            for line in ex.output.decode("UTF-8").split("\n"):
                self.log.error(ansi_escape.sub('', line))
            self.log.exception(ex)
            self.log.error("%s Failed promotion end"
                           " logs -----------------------------", log_header)
            raise PromotionError("Failed to promote overcloud images")

        os.unlink(extra_vars_path)
        if type(container_logs) is not str:
            container_logs = container_logs.decode()
        self.log.info("%s Successful promotion", log_header)
        self.log.debug("%s Successful "
                       "promotion start logs -----------------------------",
                       log_header)
        for line in container_logs.split("\n"):
            self.log.debug(ansi_escape.sub('', line))
        self.log.debug("%s Successful "
                       "promotion end logs -----------------------------",
                       log_header)
