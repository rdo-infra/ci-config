"""
This file contains classes and functionto interact with qcow images servers
to upload dockerfiles
"""
import logging
import subprocess
import sys

from common import PromotionError, get_release_map
from repo_client import RepoClient


class CopyQuayClient(object):
    """
    This class interacts with qcow images servers
    """
    log = logging.getLogger("promoter")

    def __init__(self, config):
        self.config = config
        self.release = get_release_map(config.release)
        self.git_root = self.config.git_root
        self.distro_name = self.config.distro_name
        self.distro_version = self.config.distro_version
        self.repo_client = RepoClient(self.config)
        self.extra_vars = {
            'release': self.config.release,
            'script_root': self.git_root,
            'distro_name': self.config.distro_name,
            'distro_version': self.config.distro_version,
            'manifest_push': self.config.manifest_push,
            'target_registries': self.config.target_registries,
            'source_registries': self.config.source_registry,
        }

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
            self.log.error(
                "Versions.csv does not contain tripleo-common commit")
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
            'target_namespace': self.config.target_namespace,
        }
        self.extra_vars.update(extra_vars)

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

        self.log.info("Containers promote '{}' to {}".format(candidate_hash,
                                                             target_label))

        cmd = f"{self.config.copy_quay_path} copy " \
              f"--config ~/config.yaml --release {self.config.release} " \
              f"--from-namespace {self.config.source_namespace} " \
              f"--to-namespace {self.config.target_namespace} " \
              f"--pull-registry {self.config.source_registry} " \
              f"--push-registry {self.config.target_registries[0]['url']} " \
              f"--hash {candidate_hash.commit_hash}"
        self.log.debug("Running command : {}".format(cmd))
        log_header = "Containers promote '{}' to {}:".format(candidate_hash,
                                                             target_label)
        self.log.info("%s Attempting promotion", log_header)

        # Check if candidate_hash dir is present
        try:
            self.log.debug("Checking candidate hash dir: "
                           "{}".format(candidate_hash.full_hash))
            container_logs = subprocess.Popen(cmd.split(" "),
                                              stdout=subprocess.PIPE,
                                              stderr=subprocess.STDOUT)
            for c in iter(container_logs.stdout.readline, ""):
                if not c.decode():
                    break
                sys.stdout.write(c.decode())

        except subprocess.CalledProcessError as ex:
            self.log.error("%s Failed to run copy-quay.", log_header)
            self.log.exception(ex)
            raise PromotionError(
                "{} Failed to run copy-quay.".format(log_header))

        self.log.info("%s Successful container promotion", log_header)
