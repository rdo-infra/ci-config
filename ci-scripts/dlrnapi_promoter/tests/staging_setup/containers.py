class StagingContainers(object):

    def __init__(self):
        # Select only the stagedhash with the promotion candidate
        candidate_hash_dict = \
            self.config['promotions']['promotion_candidate']
        candidate_hash = DlrnHash(source=candidate_hash_dict)
        self.stages[candidate_hash.full_hash].setup_containers()
        self.generate_pattern_file()


    def setup_containers(self):
        """
        This sets up the container both locally and remotely.
        it create a set of containers as defined in the stage-config file
        Duplicating per distribution available
        """

        base_image = BaseImage("promotion-stage-base:v1")
        if not self.config['dry-run']:
            source_image = base_image.build()

        source_registry = None
        for registry in self.config['registries']:
            if registry['type'] == "source":
                source_registry = registry
                break

        if source_registry is None:
            raise Exception("No source registry specified in configuration")

        tags = []
        pushed_images = []
        tags.append(self.dlrn_hash.full_hash)
        for arch in ['ppc64le', 'x86_64']:
            tags.append("{}_{}".format(self.dlrn_hash.full_hash, arch))

        suffixes = self.config['containers']['images-suffix']
        namespace = self.config['containers']['namespace']
        distro = self.config['distro']
        for image_name in suffixes:
            target_image_name = "{}-binary-{}".format(
                distro, image_name)
            for tag in tags:
                image = "{}/{}".format(namespace, target_image_name)
                full_image = "localhost:{}/{}".format(
                    source_registry['port'], image)
                self.log.debug("Pushing container %s:%s"
                               " to localhost:%s",
                               image, tag, source_registry['port'])
                # Skip ppc tagging on the last image in the list
                # to emulate real life scenario
                if ("ppc64le" in tag and image_name == suffixes[-1]):
                    continue
                if not self.config['dry-run']:
                    source_image.tag(full_image, tag=tag)
                image_tag = "{}:{}".format(full_image, tag)

                pushed_images.append("{}:{}".format(image, tag))

                if self.config['dry-run']:
                    continue

                self.docker_client.images.push(full_image, tag=tag)
                self.docker_client.images.remove(image_tag)

        self.config['results']['containers'] = pushed_images

        if not self.config['dry-run']:
            base_image.remove()


    def cleanup_containers(self, containers):
        """
        CANDIDATE FOR REMOVAL
        Cleans up containers remotely
        """

        for image in containers:
            # remove container remotely
            # get_registry_data()
            # curl -v -X DELETE
            # http://host:port/v2/${image_name}/manifests/${digest}
            self.log.info("removing container %s", image)
            self.log.info("remote cleanup is not implemented")

    def teardown(self):
        # We don't normally need to teardown all the containes created. The
        # containers
        # are deleted immediately after pushing them to the source registry
        os.unlink(self.config['containers']['pattern_file_path'])
