"""
This file contains classes and functionto interact with containers registries
"""
import logging
import os
import subprocess
import tempfile

import yaml

from common import PromotionError
from repo_client import RepoClient


class RegistriesClient(object):
    """
    This class interacts with containers registries
    """

    log = logging.getLogger("promoter")

    def __init__(self, config):
        self.config = config
        self.git_root = self.config.git_root
        self.logfile = self.config.log_file
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

        containers_list = self.repo_client.get_containers_list(tripleo_sha)
        if not containers_list:
            self.log.error("Containers list is empty")
            raise PromotionError

        extra_vars = {
            'candidate_label': candidate_label,
            'named_label': target_label,
            'commit_hash': candidate_hash.commit_hash,
            'distro_hash': candidate_hash.distro_hash,
            'full_hash': candidate_hash.full_hash,
            'containers_list': containers_list
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

        # Use single string to make it easy to copy/paste from logs
        cmd = (
            "env "
            "ANSIBLE_LOG_PATH={} "
            "ANSIBLE_DEBUG=False "
            "ansible-playbook -v -e @{} {}".format(
                self.logfile,
                extra_vars_path,
                self.promote_playbook,
            )
        )

        log_header = "Containers promote '{}' to {}:".format(candidate_hash,
                                                             target_label)
        try:
            self.log.info('Running: %s', cmd)
            subprocess.check_output(cmd.split(" "), stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as ex:
            os.unlink(extra_vars_path)
            self.log.exception(ex)
            self.log.error("%s Failed promotion", log_header)
            raise PromotionError("Failed to promote overcloud images")

        os.unlink(extra_vars_path)
        self.log.info("%s Successful promotion", log_header)
