"""
This file contains classes and functionto interact with qcow images servers
"""
import logging

from legacy_promoter import tag_qcow_images


class QcowClient(object):
    """
    This class interacts with qcow images servers
    """

    def __init__(self, config):
        self.config = config

    def promote_images(self, dlrn_id, target_label):
        """
        This method promotes images contained inside a dir in the server
        whose name is equal to the dlrn_id specified by creating a
        symlink to it named as the target_label
        Right now is just a wrapper around legacy code to easily pass config
        information
        :param dlrn_id:  The dlrn identifier to select images dir
        :param target_label: The name of the symlink
        :return: None
        """
        if self.config.pipeline_type == "single":
            # tag_qcow)images is imported from legacy code
            tag_qcow_images(dlrn_id, (self.config.distro_name,
                                      self.config.distro_version),
                            self.config.release,
                            target_label)
        elif self.config.pipeline_type == "component":
            self.log.error("Images promotion for aggregated hash is not yet"
                           "immplemented")
