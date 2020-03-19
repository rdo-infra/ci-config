import copy
import logging
import docker
import re

from docker_clients import DockerRegistryApiClient, DockerImagesClient


class ImageName(object):

    log = logging.getLogger("promoter")

    def __init__(self, name):
        if isinstance(name, tuple):
            registry, namespace, base_name, tag = name
        elif isinstance(name, str):
            registry, namespace, base_name, tag = self.get_parts(name)

        self.registry = registry
        self.namespace = namespace
        self.base_name = base_name
        self.tag = tag

    def get(self, parts=None):
        name = ""
        if parts is None:
            parts = ['registry', 'namespace', 'base_name', 'tag']

        if self.base_name and 'base_name' in parts:
            name = "{}".format(self.base_name)
        if self.namespace and 'namespace' in parts:
            name = "{}/{}".format(self.namespace, name)
        if self.registry and 'registry' in parts:
            name = "{}/{}".format(self.registry, name)
        if self.tag and 'tag' in parts:
            name = "{}:{}".format(name, self.tag)

        return name

    def get_parts(self, name_string):
        container_regex = (r"(\w*:[0-9]{,5})?/?([\w-]*)?/?([\w-]*):+([\w]["
                           r"\w.-]{0,127})?")
        # The regex fails in some corner cases:
        # "nova" (not rare locally)
        # "localhost:6000/nova" (rare)
        #  Both need special cases
        # For case 1 search for a / in the full_name
        if "/" not in name_string:
            parts = (None, None, name_string, None)
        # For case 2 we count the  / in the name, if we
        # have only one we are in case 2
        elif name_string.count("/") == 1:
            registry, base_name = name_string.split("/")
            parts = (registry, None, base_name, None)
        else:
            parts = re.search(container_regex, name_string).groups()

        return parts

    def change(self, registry=None, namespace=None, base_name=None, tag=None):
        if registry is not None:
            self.registry = registry
        if namespace is not None:
            self.namespace = namespace
        if base_name is not None:
            self.base_name = base_name
        if tag is not None:
            self.tag = tag

    def __str__(self):
        return self.full

    @property
    def full(self):
        return self.get()

    @property
    def full_no_tag(self):
        return self.get(parts=['registry', 'namespace', 'base_name'])

    @property
    def base_namespace(self):
        return self.get(parts=['namespace', 'base_name'])


class RegistryImage(object):

    log = logging.getLogger("promoter")

    def __init__(self, name, api_client, images_client_class=DockerImagesClient,
                 platform="x86_64"):
        if isinstance(name, tuple):
            self.name = ImageName(name)
        elif isinstance(name, ImageName):
            self.name = name
        self.client = images_client_class()
        self.local_image = None
        self.api_client = api_client
        self.platform = platform
        self.os = "linux"
        self.sub_platforms = None

    def __str__(self):
        return self.name.full

    def copy(self, source_name, locally=True, remotely=False):
        if locally:
            self.client.tag(source_name, self.name)
        if remotely:
            self.api_client.tag(source_name, self.name)

    def __repr__(self):
        return "RegistryImage platform: {}, name: {}".format(
            self.platform, self.name.full)

    def exists(self, remotely=False):
        if remotely:
            return self.api_client.exists(self.name)
        else:
            return bool(self.get_local_image())


class SingleArchImage(RegistryImage):

    def get_image(self):
        if self.local_image is None:
            self.get_local_image()
        if self.local_image is None:
            self.pull()
        if self.local_image is None:
            raise Exception("Image not found locally or remotely")

    def get_local_image(self):
        if not self.local_image:
            self.client.get(self.name)
        return self.local_image

    def __eq__(self, other):
        digest = self.client.get_digest(self.name)
        other_digest = other.client.get_digest(other.name)
        if digest is None and other_digest is None:
            return False
        return digest == other_digest

    def compare(self, other, remotely=False):
        if remotely:
            if not (self.api_client.manifest_exists(self.name.full, self.name.tag)
                    and self.api_client.manifest_exists(repo, other_tag)):
                return False
        else:
            return self == other

    def check_status(self, locally=True, remotely=False):
        status = {}
        if locally and not self.exists():
            status['missing_locally'] = self
        if remotely and not self.exists(remotely=True):
            status['missing_remotely'] = self

        return status

    def remove(self, locally=False, remotely=False):
        if locally:
            self.client.remove(self.name, force=True)
            self.local_image = None
        if remotely:
            self.api_client.image_delete(self.name.full, self.name.tag)

    def push(self):
        self.log.debug("Pushing image %s", self.name)
        self.client.push(self.name)
        self.log.debug("Image %s pushed successfully", self.name)

    def pull(self):
        self.log.debug("Pulling image: %s , tag: %s", self.name.full_no_tag,
                       self.name.tag)
        self.local_image = self.client.pull(self.name)


class MultiArchImage(RegistryImage):

    def __init__(self, *args, **kwargs):
        super(MultiArchImage, self).__init__(*args, **kwargs)
        self.platform = "multi"
        tag_x86 = "{}_x86_64".format(self.name.tag)
        tag_ppc = "{}_ppc64le".format(self.name.tag)
        name_x86 = copy.copy(self.name)
        name_x86.change(tag=tag_x86)
        name_ppc = copy.copy(self.name)
        name_ppc.change(tag=tag_ppc)

        self.sub_platforms = {
            'x86_64': SingleArchImage(name_x86,
                                      self.api_client, platform="x86_64"),
            'ppc64le': SingleArchImage(name_ppc,
                                       self.api_client, platform="ppc64le")
        }

    def set_subimage(self, image, platform):
        self.sub_platforms[platform] = image

    def remove(self, locally=False, remotely=False):
        for image in self.sub_platforms.values():
            image.remove(locally=locally, remotely=remotely)

    def check_status(self, locally=False, remotely=False):
        # Not possible to check the local status of the manifest.
        status = {}
        if remotely and not self.exists(remotely=True):
            status['missing_remotely'] = self
        return status

    def pull(self):
        for image in self.sub_platforms.values():
            image.pull()

    def push(self):
        for image in self.sub_platforms.values():
            image.push()

        # docker python does not support multiarch manifests ....
        self.api_client.manifest_list_put(self.name,
                                          self.sub_platforms.values())


