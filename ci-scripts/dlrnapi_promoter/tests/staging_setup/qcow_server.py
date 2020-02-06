from dlrn_interface import (DlrnCommitDistroHashi, DlrnHash,
                            DlrnClient, DlrnClientConfig)


class QcowStagingServer(object):

    def __init__(self, config):
        self.release = self.config.main['release']
        self.distro = self.config.main['distro']
        images_top_root = self.config.overclouc_images['root']
        self.images_root = os.path.join(images_top_root, self.distro,
                                        self.release, "rdo_trunk")
        self.commits = self.config.dlrn['commits']
        self.images_dirs = {}

    def setup(self):
        """
        For each hash, configure the images server i.e. configure local paths
        for the sftp client to promote. Paths created here mimic the hierarchy
        used by the actual images server. It also injects a single empty image
        in the path. Might consider removing as the promoter cares only about
        directories and links
        """
        if self.config['dry-run']:
            return

        self.create_hierarchy()
        self.promote_overcloud_images()
        return self.stage_info

    def promote_overcloud_images(self, promotion_target):
        """
        This function just creates a link to the images directory
        to emulate the existing links that need to be shifted when the real
        promotion happens
        """

        """
        Creates the links for the images hierarchy
        TODO: create the previous-* links
        """
        for _, promotion in self.config['results']['promotions'].items():
            # Aggregate hashes are not in the database, and we need to ask
            # the promotion name to the dlrn interfaces

            promotion_hash = DlrnHash(source=promotion)
            promotion_target = promotion_hash.name
            staged_hash = self.commits[promotion_hash.full_hash]
            staged_hash.promote_overcloud_images(promotion['name'])

            target = os.path.join(self.images_dirs[self.distro],
                                  self.dlrn_hash.full_hash)
            link = os.path.join(
                self.images_dirs[distro], promotion_target)

            if self.config['dry-run']:
                return

            try:
                os.symlink(target, link)
                self.log.info("Link %s to %s as it was promoted to %s", target,
                              link, promotion_target)
            except OSError:
                self.log.info("Overcloud images already promoted, not creating")

    def create_hierarchy(self):
        try:
            os.mkdirs(self.images_root)
            self.log.debug("Created top level images dir %s",
                           self.overcloud_images_base_dir)
        except OSError:
            self.log.info("Overcloud images dir is not empty, not creating"
                          "hierarchy")

        try:
            os.makedirs(self.config['distro_images_dir'])
            self.log.info("Created image dir %s",
                          self.config['distro_images_dir'])
        except OSError:
            self.log.debug("Reusing image dir %s",
                           self.config['distro_images_dir'])
        for commit in self.commits:
            dlrn_hash = DlrnCommitDistroHash(source=commit)
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
        stage_info = {}
        stage_info['host'] = "localhost"
        stage_info['user'] = self.promoter_user
        stage_info['key_path'] = "unknown"

        return stage_info


    def teardown(self):
        try:
            self.log.debug("removing %s", self.images_root)
            shutil.rmtree(images_root)
        except OSError:
            self.log.error("Error removing directory")
            raise


