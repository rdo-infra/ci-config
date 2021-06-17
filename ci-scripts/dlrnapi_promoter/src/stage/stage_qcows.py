"""
This file contains classes that stage an overcloud images server
"""
import logging
import os
import shutil

from promoter.dlrn_hash import DlrnHash


class QcowStagingServer(object):
    """
    Stage an ovecloud qcow images server
    """

    log = logging.getLogger("promoter-staging")

    def __init__(self, config):
        """
        like many inits around the code, this loads the config and create
        shortcuts for the used configuration parameters
        :param config: The global stage config
        """
        self.config = config
        self.release = self.config['release']
        self.distro = self.config['distro']
        self.dry_run = self.config['dry_run']
        self.images_top_root = self.config.qcow_server['root']
        self.images_root = os.path.join(self.images_top_root, self.distro,
                                        self.release, "rdo_trunk")
        self.commits = self.config.dlrn['commits']
        self.images_dirs = {}
        self.promotions = self.config.dlrn['promotions']
        self.promoter_user = self.config['promoter_user']

    def setup(self):
        """
        For each hash, configure the images server i.e. configure local paths
        for the sftp client to promote. Paths created here mimic the hierarchy
        used by the actual images server. It also injects a single empty image
        in the path.
        :return: None
        """
        if self.dry_run:
            return

        try:
            os.makedirs(self.images_root)
            self.log.debug("Created top level images dir %s",
                           self.images_root)
        except OSError:
            self.log.info("Overcloud images dir is not empty, not creating"
                          "hierarchy")

        self.create_hierarchy()
        self.promote_overcloud_images()
        return self.stage_info

    def promote_overcloud_images(self):
        """
        This function just creates a link to the images directory
        to emulate the existing links that need to be shifted when the real
        promotion happens
        :return: None
        """

        # TODO(gcerami): create the previous-* links
        for __, promotion_commit in self.promotions.items():
            promotion_hash = DlrnHash(source=promotion_commit)
            promotion_target = promotion_commit['name']

            target_dir = os.path.join(self.images_root,
                                      promotion_hash.full_hash)
            link = os.path.join(self.images_root, promotion_target)

            try:
                os.symlink(target_dir, link)
                self.log.info("Link %s to %s as it was promoted to %s",
                              target_dir,
                              link, promotion_target)
            except OSError:
                self.log.info("Overcloud images already promoted, not creating")

    def create_hierarchy(self):
        """
        Creates the basic hierarchy for all the hashes, and injects an empty
        image in the directory
        :return: None
        """
        for commit in self.promotions.values():
            dlrn_hash = DlrnHash(source=commit)
            image_name = "{}-image.tar.gz".format(dlrn_hash.full_hash)
            image_dir = os.path.join(self.images_root, dlrn_hash.full_hash)
            image_path = os.path.join(image_dir, image_name)
            try:
                os.mkdir(image_dir)
                self.log.info("Created image dir in %s", image_dir)
            except OSError:
                self.log.info("Reusing image in %s", image_path)
            self.log.info("Creating empty image in %s", image_dir)
            # This emulates a "touch" command
            with open(image_path, 'w'):
                pass

    @property
    def stage_info(self):
        """
        Property that returns the dict with info on the created images server
        :return: A dict with useful info
        """
        stage_info = {
            'host': "localhost",
            'user': self.promoter_user,
            'key_path': "unknown",
            'root': self.images_top_root.rstrip("/")
        }

        return stage_info

    def teardown(self, __):
        """
        Clean up the images subtree
        :param __: An unused parameter useful for other teardown methods
        :return: None
        """
        try:
            self.log.debug("removing %s", self.images_top_root)
            shutil.rmtree(self.images_top_root)
        except OSError:
            self.log.error("Error removing directory")
            raise
