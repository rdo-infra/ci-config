import logging

from docker_clients import DockerRegistryApiClient


class RegistryClient(object):

    log = logging.getLogger("promoter")

    def __init__(self, config, images_sets, allow_status_check=False,
                 api_client_class=DockerRegistryApiClient):
        self.config = config
        self.images_sets = images_sets
        self.allow_status_check = allow_status_check
        self.api_client = api_client_class(config)
        self.namespace = config['namespace']
        self.host = config['host']
        self.port = config['port']
        self.registry = "{}:{}".format(self.host, self.port)
        # self.driver = config['driver']
        self.api_client = api_client_class(config)
        self.driver = "docker"
        self.base_names = None
        self.candidate_tag = None
        self.target_tag = None

    def set_promotion_parameters(self, base_names, candidate_tag,
                                 target_tag):
        self.base_names = base_names
        self.candidate_tag = candidate_tag
        self.target_tag = target_tag
        self.images_sets.reset_all(self)


class TargetRegistryClient(RegistryClient):

    def __init__(self, *args, **kwargs):
        super(TargetRegistryClient, self).__init__(*args, **kwargs)
        self.images_to_upload = self.images_sets.create_set(self, "to_upload")
        self.images_to_promote = self.images_sets.create_set(self, "to_promote")
        self.images_expected = self.images_sets.create_set(self, "expected")
        self.images_promoted = self.images_sets.create_set(self, "promoted")

    def set_promotion_parameters(self, *args, **kwargs):
        super(TargetRegistryClient, self).set_promotion_parameters(*args,
                                                                   **kwargs)

        self.images_expected.add_images(self.base_names)

        if self.allow_status_check:
            self.check_status()
        else:
            self.images_to_upload.add_images(self.base_names,
                                             self.candidate_tag)
            self.images_to_promote.add_images(self.base_names,
                                              self.candidate_tag)

        self.log.debug("Images to upload to %s: %s",
                       self.registry, self.images_to_upload)
        self.log.debug("Images to promote in %s: %s",
                       self.registry, self.images_to_promote)

    def check_status(self):
        # check for images:dlrn_hash that are not in target registry and
        # for images that are different from images:target_label (meaning
        # they were not promoted to target_label)
        # check images tagged with hash, compare digests with same images
        # with target_label as tag
        status = self.images_expected.check_set_status(
            locally=False,
            remotely=True,
            compare_tag=self.target_tag)

        self.images_to_upload.add_images(status['missing_remotely'])
        self.images_to_promote.add_images(status['digest_mismatch'])

    def upload_images(self, source_set):
        self.images_to_upload.reassign(source_set.registry_client,
                                       source_set.set_name)
        self.images_to_upload.push()

    def promote_images(self):
        promoted_images = self.images_to_promote.promote(self.target_tag,
                                                         locally=False,
                                                         remotely=True)
        self.images_promoted.add_images(promoted_images)

    def validate_promotion(self):
        return self.images_promoted == self.images_expected


class SourceRegistryClient(RegistryClient):

    def __init__(self, *args, **kwargs):
        super(SourceRegistryClient, self).__init__(*args, **kwargs)
        self.images_to_check = self.images_sets.create_set(self, "to_upload")
        self.images_to_promote = self.images_sets.create_set(self, "to_promote")
        self.images_to_download = self.images_sets.create_set(self,
                                                              "to_download")
        self.images_promoted = self.images_sets.create_set(self, "promoted")
        self.images_downloaded = self.images_sets.create_set(self, "downloaded")

    def check_status(self):
        status = self.images_to_check.check_status(
            remotely=True,
            compare_tag=self.target_tag)
        if status['missing']['x86_64']['remotely']:
            raise Exception("Missing mandatory images in source registry")

        # What images we need to download ?
        # We start from the locally missing ppc64, then remove the ones we know
        # they are not in source registry
        # Finally add all the locally missing x86_64 images

        images_to_download = \
            status['missing']['ppc64le']['locally'].difference(
                status['missing']['ppc64le']['remotely'])
        images_to_download = images_to_download.union(
            status['missing']["x86_64"]["locally"])
        self.images_to_download.add_images(images_to_download)
        self.log.debug("Images to download to %s: %s", self.registry,
                       images_to_download)
        # More or less same thing for images to promote
        images_to_promote = \
            status['digest_mismatch']['ppc64le'].difference(
                status['missing']['ppc64le'])
        images_to_promote = images_to_promote.union(
            status['digest_mismatch']["x86_64"])
        self.images_to_promote.add_images(images_to_promote)
        self.log.debug("Images to promote in %s: %s", self.registry,
                       images_to_promote)

    def download_images(self):
        self.log.debug("Downloading Image from list to download")
        downloaded_images = self.images_to_download.pull()
        self.images_downloaded.add_images(downloaded_images)

    def promote_images(self):
        promoted_images = self.images_to_promote.promote(self.target_tag)
        self.images_promoted.add_images(promoted_images, tag=self.target_tag)
