import logging

from docker_clients import DockerRegistryApiClient
from registry_image import SingleArchImage


class SetHandle(object):
    """
    Proxy class to pass to registry.
    """

    def __init__(self, parent, registry_client, set_name):
        self.parent = parent
        self.registry_client = registry_client
        self.set_name = set_name

    def add_images(self, *args, **kwargs):
        self.parent.add_images_to_set(self.registry_client, self.set_name,
                                      *args, **kwargs)

    def get_set(self):
        return self.parent.get_set(self.registry_client, self.set_name)

    def check_status(self, *args, **kwargs):
        return self.parent.check_set_status(self.registry_client,
                                            self.set_name, *args, **kwargs)

    def reset(self):
        self.parent.reset(self.registry_client, self.set_name)

    def push(self, *args, **kwargs):
        return self.parent.push_set(self.registry_client,
                                    self.set_name, *args, **kwargs)

    def pull(self, *args, **kwargs):
        return self.parent.pull_set(self.registry_client,
                                    self.set_name, *args, **kwargs)

    def promote(self, *args, **kwargs):
        return self.parent.retag(self.registry_client,
                                 self.set_name, *args, **kwargs)

    def reassign(self, *args, **kwargs):
        return self.parent.reassign(self.registry_client,
                                    self.set_name, *args, **kwargs)


class ImagesSets(object):

    log = logging.getLogger("promoter")

    def __init__(self, default_images_class=SingleArchImage):
        self.sets = {}
        self.default_images_class = default_images_class

    def get_set(self, registry_client, set_name):
        set_id = (registry_client, set_name)
        return self.sets[set_id]

    def create_set(self, registry_client, set_name,
                   image_class=SingleArchImage,
                   images=None, tag=None):
        set_id = (registry_client, set_name)
        self.sets[set_id] = set()
        if images is not None and tag is not None:
            self.add_images_to_set(registry_client, set_name, images, tag,
                                   image_class=image_class)
        else:
            self.log.debug("No images added at list creation")

        return SetHandle(self, registry_client, set_name)

    def copy_set(self, src_set, dest_set):
        src_images = src_set.get_set()
        self.add_images_to_set(dest_set.registry_client, dest_set.set_name,
                               src_images)

    def add_images_to_set(self, registry_client, set_name, images, tag=None,
                          image_class=None):
        if image_class is None:
            image_class = self.default_images_class
        image_set = self.get_set(registry_client, set_name)

        if not isinstance(images, list) and not isinstance(images, set):
            self.log.debug("Images source is not iterable")
            images = [images]

        for image in images:
            if isinstance(image, str):

                base_name = image
                image = image_class((registry_client.registry,
                                     registry_client.namespace,
                                     base_name, tag),
                                    registry_client.api_client)
            elif isinstance(image, image_class):
                if tag is None:
                    tag = image.name.tag
                image = image_class((registry_client.registry,
                                     registry_client.namespace,
                                     image.name.base_name,
                                     tag),
                                    registry_client.api_client)

            self.log.debug("Adding image to the set %s: %s",
                           set_name, str(image))
            image_set.add(image)

        self.log.debug("Added images to the set %s: %s",
                       set_name, ", ".join(map(str, image_set)))

    def reset_all(self, requesting_registry_client):
        for set_id in self.sets.keys():
            registry_client, set_name = set_id
            if registry_client == requesting_registry_client:
                self.reset(registry_client, set_name)

    def reset(self, registry_client, set_name):
        self.sets[(registry_client, set_name)] = set()

    def pull_set(self, registry_client, set_name):
        images_set = self.get_set(registry_client, set_name)
        pulled_images = set()
        self.log.debug("pulling all images in list %s: %s", set_name,
                       images_set)
        for image in images_set:
            image.pull()
            pulled_images.add(image)

        return pulled_images

    def push_set(self, registry_client, set_name):
        images_set = self.get_set(registry_client, set_name)
        pushed_set = set()
        self.log.debug("pushing all images in list %s: %s", set_name,
                       images_set)
        for image in images_set:
            image.push()
            pushed_set.add(image)

        return pushed_set

    def reassign(self, registry_client, set_name, src_registry_client,
                 src_set_name, remotely=False):
        images_set = self.get_set(src_registry_client, src_set_name)
        reassigned_set = set()
        for source_image in images_set:
            reassigned_image = self.default_images_class((
                registry_client.registry, registry_client.namespace,
                source_image.name.base_name, source_image.name.tag),
                registry_client.api_client)
            reassigned_image.create(source_image)
            reassigned_set.add(reassigned_image)

        self.add_images_to_set(registry_client, set_name, reassigned_set)

        return reassigned_set

    def retag(self, registry_client, set_name, new_tag, locally=False,
              remotely=False):
        images_set = self.get_set(registry_client, set_name)
        retagged_set = set()
        for source_image in images_set:
            retagged_image = self.default_images_class((
                registry_client.registry, registry_client.namespace,
                source_image.name.base_name, new_tag),
                registry_client.api_client)
            retagged_image.create(source_image,
                                  locally=locally, remotely=remotely)
            retagged_set.add(retagged_image)

        return retagged_set

    def check_set_status(self, registry_client, set_name, locally=True,
                         remotely=False,
                         compare_tag=None):
        images_set = self.get_set(registry_client, set_name)

        set_status = {
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

        for image in images_set:
            image_status = image.check_status(locally=locally,
                                              remotely=remotely,
                                              compare_tag=compare_tag)

            self.log.debug("set %s image %s status: %s", set_name,
                           image.name.full, image_status)
            try:
                set_status['missing'][image.platform]['locally'].update(
                    image_status['missing_locally'])
            except KeyError:
                pass
            try:
                set_status['missing'][image.platform]['remotely'].update(
                    image_status['missing_remotely'])
            except KeyError:
                pass
            try:
                set_status['digest_mismatch'][image.platform].update(
                    image_status['digest_mismatch'])
            except KeyError:
                pass

        self.log.debug("image set %s status: %s", set_name, set_status)

        return set_status

    def search(self, registry_client, set_name, filters):
        ''' filters is a dictionary of field:regex to apply to container
        '''
        filtered_set = set()

        # If there are no filters, nothing matches
        if not filters:
            return filtered_set

        images_set = self.get_set(registry_client, set_name)

        for image in images_set:
            res = []
            for key, value in filters.items():
                res.append(bool(re.search(value, getattr(image.name, key))))
            if all(res) and res is not []:
                filtered_set.add(image)

        return filtered_set
