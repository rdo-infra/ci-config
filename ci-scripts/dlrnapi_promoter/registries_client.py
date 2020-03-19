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

from common import PromotionError
from repo_client import RepoClient
from registry_client import TargetRegistryClient, SourceRegistryClient


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

        self.extra_vars = {
            'release': self.config.release,
            'script_root': self.git_root,
            'distro_name': self.config.distro_name,
            'distro_version': self.config.distro_version,
            'manifest_push': self.config.manifest_push,
            'target_registries_push': self.config.target_registries_push
        }
        self.repo_client = RepoClient(self.config)

    def get_containers_list(self, candidate_hash, candidate_label):
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
        return containers_list

    def prepare_extra_vars(self, candidate_hash, target_label, candidate_label):
        containers_list = self.get_containers_list(candidate_hash,
                                                   candidate_label)
        if not containers_list:
            self.log.error("containers list is empty")
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


class RegistriesOrchestrator(RegistriesClient):

    log = logging.getLogger("promoter")

    def __init__(self, config):
        super(RegistriesOrchestrator, self).__init__(config)
        self.source_registry = SourceRegistryClient(config.registries['source'])
        self.target_registries = {}
        for registry_config in config.registries['targets']:
            self.target_registries[registry_config['name']] = \
                TargetRegistryClient(registry_config)

        self.base_names = None
        self.validations = {}
        self.validations['source_registry'] = {}
        self.validations['target_registries'] = []
        self.iamge_sets = ImagesSets()

    def get_containers_list(self, candidate_hash, candidate_label):
        partial_names = super(RegistriesOrchestrator, self).get_containers_list(
            candidate_hash, candidate_label)
        partial_names.append("base")
        partial_names.append("openstack-base")
        base_names = \
            list(map(lambda partial_name: "{}-binary-{}"
                                          "".format(self.config.distro_name,
                                                    partial_name),
                     partial_names))

        if not base_names:
            self.log.error("containers list is empty")
            raise PromotionError

        return base_names

    def promote_experimental(self, candidate_hash, target_label,
                             candidate_label=None):

        base_names = self.get_containers_list(candidate_hash, candidate_label)

        self.log.debug("Setting promotion parameters for source registry")
        self.source_registry.set_promotion_parameters(base_names,
                                                      candidate_hash,
                                                      target_label)
        self.log.debug("Promotion for target registries %s",
                       ", ".join(map(lambda r:
                                     r.registry,
                                     self.target_registries.values())))

        try:
            for registry in self.target_registries.values():
                self.log.debug("setting promotion parameter for target "
                               "registry %s", registry.registry)
                registry.set_promotion_parameters(base_names, candidate_hash,
                                                  target_label)

                self.log.debug("adding images to download for the source "
                               "registry: %s", registry.lists.to_upload)
                self.source_registry.lists.to_check.add_images(
                    registry.lists.to_upload)

            self.log.debug("Images to check in %s: %s",
                           self.source_registry.registry,
                           self.source_registry.lists.to_check)
            self.source_registry.check_status()

            self.log.info("Promoting images in the source registry, from  %s "
                          "to %s", candidate_hash.full_hash, target_label)
            self.source_registry.promote_images()
            self.log.info("Downloading images from the source registry")
            downloaded = self.source_registry.download_images()

            for registry in self.target_registries.values():
                self.log.info("Uploading images to registry %s",
                              registry.registry)
                registry.upload_images(downloaded)
                self.log.info("Promoting images in registry %s from %s to "
                              "%s", registry.registry,
                              candidate_hash.full_hash, target_label)
                registry.promote_images()

                if not registry.validate_promotion:
                    raise Exception
        except Exception:
            raise
        finally:
            self.log.info("Cleaning up images relative to source registry")
            self.source_registry.cleanup()
            for registry in self.target_registries.values():
                self.log.info(
                    "Cleaning up images relative to target registry %s",
                    registry.registry)
                registry.cleanup()
