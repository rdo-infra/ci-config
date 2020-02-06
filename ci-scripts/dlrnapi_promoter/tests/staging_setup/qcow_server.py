class QcowStagingServer(object):

    def __init__(self):


        self.images_dirs = {}
        distro_path = "{}{}".format(self.config['distro'],
                                    self.config['distro_version'])
        image_dir = os.path.join(self.overcloud_images_base_dir, distro_path,
                                 self.config['release'], "rdo_trunk")
        self.config['distro_images_dir'] = image_dir

        self.overcloud_images_base_dir = \
            self.config['overcloud_images']['base_dir']


    def setup(self):
        try:
            os.mkdir(self.overcloud_images_base_dir)
            self.log.debug("Created top level images dir %s",
                           self.overcloud_images_base_dir)
        except OSError:
            self.log.info("Overcloud images dir is not empty, not creating"
                          "hierarchy")

        self.config['results']['overcloud_images'] = {}
        self.config['results']['overcloud_images']['base_dir'] = \
            self.overcloud_images_base_dir
        self.config['results']['overcloud_images']['host'] = "localhost"
        self.config['results']['overcloud_images']['user'] = \
            self.config['promoter_user']

        self.config['results']['overcloud_images']['key_path'] = "unknown"

        if not self.config['dry-run']:
            try:
                os.makedirs(self.config['distro_images_dir'])
                self.log.info("Created image dir %s",
                              self.config['distro_images_dir'])
            except OSError:
                self.log.debug("Reusing image dir %s",
                               self.config['distro_images_dir'])
        # Use the dlrn hashes defined in the fixtures to setup all
        # the needed component per-hash
        for __, stage in self.stages.items():
            stage.prepare_environment()

        self.promote_overcloud_images()


    def promote_overcloud_images(self, promotion_target):
        """
        This function just creates a link to the images directory
        to emulate the existing links that need to be shifted when the real
        promotion happens
        """
        distro = self.config['distro']
        target = os.path.join(self.images_dirs[distro],
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

    def setup_images(self):
        """
        For each hash, configure the images server i.e. configure local paths
        for the sftp client to promote. Paths created here mimic the hierarchy
        used by the actual images server. It also injects a single empty image
        in the path. Might consider removing as the promoter cares only about
        directories and links
        """
        distro_images_dir = self.config['distro_images_dir']
        image_name = "{}-image.tar.gz".format(self.dlrn_hash.full_hash)
        image_path = os.path.join(distro_images_dir, self.dlrn_hash.full_hash,
                                  image_name)
        self.images_dirs[self.config['distro']] = distro_images_dir

        if self.config['dry-run']:
            return

        try:
            hash_dir = os.path.join(distro_images_dir, self.dlrn_hash.full_hash)
            os.mkdir(hash_dir)
            self.log.info("Created image dir in %s", hash_dir)
        except OSError:
            self.log.info("Reusing image in %s", image_path)
        self.log.info("Creating empty image in %s", hash_dir)
        # This emulates a "touch" command
        with open(image_path, 'w'):
            pass

    def prepare_environment(self):
        """
        Orchestrator for the single stage component setup
        """
        if (self.config['components'] == "all"
                or "overcloud-images" in self.config['components']):
            self.setup_images()

    def promote_overcloud_images(self):
        """
        Creates the links for the images hierarchy
        TODO: create the previous-* links
        """
        for _, promotion in self.config['results']['promotions'].items():
            promotion_hash = DlrnHash(source=promotion)
            staged_hash = self.stages[promotion_hash.full_hash]
            staged_hash.promote_overcloud_images(promotion['name'])

    def teardown(self):
        directory = self.config['overcloud_images']['base_dir']
        try:
            self.log.debug("removing %s", directory)
            shutil.rmtree(directory)
        except OSError:
            self.log.error("Error removing directory")
            raise


