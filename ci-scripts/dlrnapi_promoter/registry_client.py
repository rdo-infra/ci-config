import logging

from containers_lists import ImageList
from docker_clients import DockerRegistryApiClient

class registryHandle(object):
    """
    Proxy class to pass to registry.
    """

    def __init__(self, parent, registry_client, set_name):
        self.parent = parent
        self.registry_client = registry_client
        self.set_name = set_name

    def add_images(self, tag, images):
        self.parent.add_images_to_set(self.registry_client, self.set_name,
                                      tag, images)


class ImagesSets(object):

    log = logging.getLogger("promoter")

    def __init__(self, registry, namespace, api_client):
        self.sets = {}

    def get_set(self, registry_client, set_name):
        set_id = (registry_client, set_name)
        return self.sets[set_id]

    def create_set(self, registry_client, set_name, tag,
                   image_class=SingleArchImage,
                   images=None):
        set_id = (registry_client, set_name)
        self.sets[set_id] = set()
        if images is not None:
            self.add_images_to_set(registry_client, set_name, images, tag,
                                   image_class=image_class)
        else:
            self.log.debug("No images added at list creation")

        return registry_handle

    def change_tag_in_set(self, registry_client, set_name, tag):
        pass

    def add_images_to_set(self, registry_client, set_name, images, tag,
                          image_class=SingleArchImage):
        image_set = self.get_set(registry_client, set_name)

        if not isinstance(images, list) and not isinstance(images, set):
            self.log.debug("Images source is not iterable")
            images = [images]

        for image in images:
            if isinstance(image, str):

                base_name = image
                image = self.image_class((self.registry, self.namespace,
                                          base_name, self.tag), self.api_client)
            elif isinstance(image, self.image_class):
                image = self.image_class((registry_client.registry,
                                          registry_client.namespace,
                                          image.name.base_name,
                                          image.name.tag),
                                         registry_client.api_client)

            self.log.debug("Adding image to the set %s: %s",
                           set_name, str(image))
            image_set.add(image)

        self.log.debug("Added images to the set %s: %s",
                       set_name, ", ".join(map(str, image_set)))

    def pull_set(self, remove_from_list=False):
        pulled_images = []
        self.log.debug("pulling all images in list %s: %s", self.name,
                       ", ".join(map(str, self.images)))
        if remove_from_list:
            images_list = self.images
        else:
            images_list = copy.copy(self.images)
        while images_list:
            image = images_list.pop()
            image.pull()
            pulled_images.append(image)

        return pulled_images

    def push_set(self, registry_client, set_name, remove_from_set=False):
        pushed_images = []
        image_set =
        self.log.debug("pushing all images in list %s: %s", self.name,
                       ", ".join(map(str, self.images)))
        if remove_from_list:
            images_list = self.images
        else:
            images_list = copy.copy(self.images)
        while images_list:
            image = images_list.pop()
            image.push()
            pushed_images.append(image)

        return pushed_images

    def rename(self, registry, namespace, base_name, tag, locally=False,
               remotely=False):
        for image in self.images:
            image.rename(registry, namespace, base_name, tag, locally=locally,
                         remotely=remotely)

    def reassign(self, registry, namespace, locally=False, remotely=False):
        self.rename(registry, namespace, None, None)

    def retag(self, new_tag, locally=False, remotely=False):
        retagged_images = []
        for image in self.images:
            retagged_images.append(image.retag(new_tag, locally=locally,
                                               remotely=remotely))

        return retagged_images
    def reassign_list(self, src_list, dst_list):
        new_list = self.create(src_list.tag,

    def check_set_status(self, locally=True, remotely=False, compare_tag=None):
        missing_locally = []
        missing_remotely = []
        digest_mismatch = []
        status = {
            'missing': {
                'multiarch': {
                    'locally': set(),
                    'remotely': set(),
                },
                'x86_64': {
                    'locally': set(),
                    'remotely': set(),
                },
                'ppc64le': {
                    'locally': set(),
                    'remotely': set(),
                },
            },
            'digest_mismatch': {
                'multiarch': set(),
                'x86_64': set(),
                'ppc64le': set(),
            },
        }

        for image in self.images:
            status = image.check_status(locally=locally,
                                        remotely=remotely,
                                        compare_tag=compare_tag)
            self.log.debug(
                "list %s image %s status: missing locally: %s, missing "
                "remotely "
                "%s, digest mismatched %s", self.name, image,
                status['missing_locally'],
                status['missing_remotely'],
                status['digest_mismatch'])
            if status['missing_locally']:
                missing_locally += status['missing_locally']
            if status['missing_remotely']:
                missing_remotely += status['missing_remotely']
            if status['digest_mismatch']:
                digest_mismatch += status['digest_mismatch']

        if not locally:
            missing_locally = None
        if not remotely:
            missing_remotely = None
        self.log.debug(
            "image list %s status: missing locally: %s, missing remotely "
            "%s, digest mismatched %s", self.name,
            missing_locally,
            missing_remotely,
            digest_mismatch)
        self.status = {
            'missing_locally': missing_locally,
            'missing_remotely': missing_remotely,
            'digest_mismatch': digest_mismatch,
        }

        return registry_handle

    def search(self, filters):
        ''' filters is a dictionary of field:regex to apply to container
        '''
        filtered_containers = []

        # If there are no filters, nothing matches
        if not filters:
            return []

        for image in self.images:
            res = []
            for key, value in filters.items():
                res.append(bool(re.search(value, getattr(image.name, key))))
            if all(res) and res is not []:
                filtered_containers.append(image)

        return filtered_containers


class RegistryClient(object):

    log = logging.getLogger("promoter")

    def __init__(self, config, allow_status_check=False,
                 api_client_class=DockerRegistryApiClient):
        self.config = config
        self.allow_status_check = allow_status_check
        self.api_client = api_client_class(config)
        self.namespace = config['namespace']
        self.host = config['host']
        self.port = config['port']
        self.registry = "{}:{}".format(self.host, self.port)
        #self.driver = config['driver']
        self.api_client = api_client_class(config)
        self.driver = "docker"
        self.base_names = None

    def set_promotion_parameters(self, base_names, candidate_hash,
                                 target_label):
        self.base_names = base_names
        self.candidate_hash = candidate_hash
        self.target_label = target_label

    def cleanup(self):
        for list_name in self.lists.lists:
            images_list = getattr(self.lists, list_name)
            images_list.local_remove()


class TargetRegistryClient(RegistryClient):

    def set_promotion_parameters(self, base_names, candidate_hash,
                                 target_label):
        super(TargetRegistryClient, self).set_promotion_parameters(
            base_names, candidate_hash, target_label)
        self.lists.create(candidate_hash.full_hash, name="to_upload")
        self.lists.create(candidate_hash.full_hash, name="to_promote")
        self.lists.create(candidate_hash.full_hash, name="to_download")
        if self.allow_status_check:
            self.check_status()
        else:
            self.lists.to_upload.add_images(base_names)
            self.lists.to_download.add_images(base_names)
            self.lists.to_promote.add_images(base_names)

        self.log.debug("Images to upload to %s: %s",
                       self.registry, self.lists.to_upload)
        self.log.debug("Images to download for %s: %s",
                       self.registry, self.lists.to_download)
        self.log.debug("Images to promote in %s: %s",
                       self.registry, self.lists.to_promote)

    def check_status(self):
        # check for images:dlrn_hash that are not in target registry and
        # for images that are different from images:target_label (meaning
        # they were not promoted to target_label)
        # check images tagged with hash, compare digests with same images
        # with target_label as tag
        status = self.lists.uploaded.check_images_status(
            locally=False,
            remotely=True,
            compare_tag=self.target_label)

        self.lists.to_upload.add_images(status['missing_remotely'])
        self.lists.to_promote.add_images(status['digest_mismatch'])

    def upload_images(self, downloaded):
        self.log.debug("Retagging images to upload to registry")
        self.lists.reassign(
        downloaded.reassign_(self.registry, self.namespace, locally=True,
                            remotely=False)
        uploaded_images = self.lists.to_upload.push(remove_from_list=True)
        self.lists.create(self.candidate_hash.full_hash,
                          name="uploaded",
                          images=uploaded_images)

    def promote_images(self):
        promoted_images = self.lists.to_promote.push(remove_from_list=True)
        self.lists.create(self.candidate_hash.full_hash,
                          name="promoted",
                          images=promoted_images)

    def validate_promotion(self):
        return self.lists.promoted == self.lists.expected


class SourceRegistryClient(RegistryClient):

    def set_promotion_parameters(self, base_names, candidate_hash,
                                 target_label):
        super(SourceRegistryClient, self).set_promotion_parameters(
            base_names, candidate_hash, target_label)
        self.lists.create(candidate_hash.full_hash, name="to_promote")
        self.lists.create(candidate_hash.full_hash, name="to_check")
        self.lists.create(candidate_hash.full_hash, name="to_download")
        self.lists.create(candidate_hash.full_hash, name="to_download_optional")

    def check_status(self):
        status = self.lists.to_check.check_status(
            remotely=True,
            compare_tag=self.target_label)
        #if status['missing_remotely'].search('_x86_64'):
        #    raise Exception("Missing images in source registry")

        self.lists.to_download.add_images(status['missing_locally'])
        self.log.debug("Images to download to %s: %s", self.registry,
                       status['missing_locally'])
        #self.lists.to_download_optional.add_images(status[
        #                                          'missing_locally_optional'])
        self.lists.to_promote.add_images(status['digest_mismatch'])
        self.log.debug("Images to promote in %s: %s", self.registry,
                       status['digest_mismatch'])

    def download_images(self):
        self.log.debug("Downloading Image from list to download")
        downloaded_images = self.lists.to_download.pull(remove_from_list=True)
        self.lists.create(self.candidate_hash.full_hash,
                          name="downloaded",
                          images=downloaded_images)
        return self.lists.downloaded

    def promote_images(self):
        promoted_images = self.lists.to_promote.retag(self.target_label,
                                                locally=False, remotely=True)
        self.lists.create(self.candidate_hash.full_hash,
                          name="promoted",
                          images=promoted_images)

