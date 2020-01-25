"""
This file contains classes and functionto interact with containers registries
"""
import logging

from legacy_promoter import tag_containers


class RegistryClient(object):
    """
    This class interacts with containers registries
    """

    log = logging.getLogger("promoter")

    def __init__(self, config):
        self.config = config

    def promote_containers(self, dlrn_id, target_label):
        """
        This method promotes containers whose tag is equal to the dlrn_id
        specified by retagging them with the target_label
        Right now is just a wrapper around legacy code to easily pass config
        information
        :param dlrn_id:  The dlrn identifier to select container tags
        :param target_label: the new tag to apply to the containers
        :return: None
        """
        if self.config.pipeline_type == "single":
            # tag_containers is imported from legacy code
            tag_containers(dlrn_id, (self.config.distro_name,
                                     self.config.distro_version),
                           self.config.release,
                           target_label, self.config.manifest_push,
                           self.config.target_registries_push)
        elif self.config.pipeline_type == "component":
            self.log.error("Container promotion for aggregated hash is not yet"
                           "immplemented")
