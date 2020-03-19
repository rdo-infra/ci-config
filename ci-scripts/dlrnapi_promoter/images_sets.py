import copy
import logging

from registry_image import SingleArchImage, MultiArchImage


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

    def __init__(self, default_images_class=MultiArchImage):
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
            reassigned_image.copy(source_image.name)
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
            retagged_image.copy(source_image.name,
                                locally=locally, remotely=remotely)
            retagged_set.add(retagged_image)

        return retagged_set

    def check_set_status(self, registry_client, set_name, locally=True,
                         remotely=False,
                         compare_tag=None):
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
                'x86_64': set(),
                'ppc64le': set(),
            },
        }

        images_set = copy.copy(self.get_set(registry_client, set_name))

        while images_set:
            image = images_set.pop()
            # If the image is a multiplatform, add images to the set we are
            # checking
            if image.sub_platforms:
                for image in image.sub_platforms.values():
                    images_set.add(image)
                continue

            # Check existence
            image_status = image.check_status(locally=locally,
                                              remotely=remotely)

            self.log.debug("set %s image %s status: %s", set_name,
                           image.name.full, image_status)
            try:
                set_status['missing'][image.platform]['locally'].add(
                    image_status['missing_locally'])
            except KeyError:
                pass

            try:
                set_status['missing'][image.platform]['remotely'].add(
                    image_status['missing_remotely'])
            except KeyError:
                pass

            # Check difference (no difference needed for multiplatform image)
            if image.platform != "multi":
                promoted_name = copy.copy(image.name)
                promoted_name.change(tag=compare_tag)
                promoted_image = image.__class__(promoted_name,
                                                 image.api_client,
                                                 platform=image.platform)
                if image.compare(promoted_image):
                    set_status['digest_mismatch'][image.platform].add(image)

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

    def remove_all_sets(self):
        for set_id, images_set in self.sets.items():
            registry_client, set_name = set_id
            self.log.info("Cleaning up set %s from registry %s",
                          set_name, registry_client.registry)
            for image in images_set:
                self.log.info("Locally removing image %s", image.name.full)
                image.remove(locally=True)

