import json
import logging
import copy
import docker
import re

from docker_clients import DockerRegistryApiClient, DockerClient


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

    def change(self, registry, namespace, base_name, tag):
        if registry is not None:
            self.registry = registry
        if namespace is not None:
            self.namespace = namespace
        if base_name is not None:
            self.base_name = base_name
        if tag is not None:
            self.tag = tag

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

    def __init__(self, name, api_client, images_client_class=DockerClient,
                 platform="x86_64"):
        self.name = ImageName(name)
        self.images_client = images_client_class()
        self.physical_image = None
        self.api_client = api_client
        self.status = {
            'missing_locally': True,
            'missing_remotely': True
        }
        self.platform = platform
        self.os = None
        self.variant = None

    def __str__(self):
        return self.name.full

    def pull(self, platform="x86_64"):
        self.log.debug("Pulling image: %s , tag: %s", self.name.full_no_tag,
                       self.name.tag)
        try:
            self.physical_image = self.images_client.pull(
                self.name.full_no_tag,
                tag=self.name.tag)
        except docker.errors.ImageNotFound:
            self.log.error("No image associated with this repo")
            raise

    def create(self, source_image, locally=True, remotely=False):
        if locally:
            source_image.local_retag(self.name.full_no_tag, self.name.tag)
        if remotely:
            self.remote_retag(source_image, self.name.tag)

    def local_retag(self, full_name_no_tag, tag):
        self.get_image()
        self.physical_image.tag(full_name_no_tag, tag)

    def retag(self, dest_tag, locally=True, remotely=False):
        if locally:
            self.local_retag(dest_tag)
        if remotely:
            self.remote_retag(dest_tag)

    def remote_retag(self, source_image, tag):
        manifest = self.api_client.manifest_get(
            source_image.name.base_namespace,
            source_image.name.tag)
        self.api_client.manifest_put(manifest, self.name.base_namespace,
                                     self.name.tag)

    def __str__(self):
        return "{}".format(self.name.full)

    def __repr__(self):
        return "RegistryImage platform: {}, name: {}".format(
            self.platform, self.name.full)


class MultiArchImage(RegistryImage):

    def __init__(self, name, images_client_class=DockerClient,
                 api_client_class=DockerRegistryApiClient):
        super(MultiArchImage, self).__init__()
        target_label_x86 = "{}_x86_64".format(self.name.tag)
        target_label_ppc = "{}_ppc64le".format(self.name.tag)
        self.x86_image = None
        self.ppc_image = None

    def __eq__(self, other):
        if not (self.api_client.manifest_exists(self.full, self.tag)
                and self.manifest_exists(repo, other_tag)):
            return False

        manifest = self.api_client.manifest_get(repo, tag)
        other_manifest = self.api_client.manifest_get(repo, other_tag)
        digest = manifest['config']['digest']
        other_digest = other_manifest['config']['digest']

        return digest == other_digest

    def create_manifest(self):
        # docker python does not support multiarch manifests ....
        # push x86
        # push ppc
        # push manifest list.
        pass

    def pull_singlearch(self):
        self.x86_image.pull()
        if self.ppc_image is not None:
            self.ppc_image.pull()

    def pull_multiarch(self):
        self.image.pull("linux/amd64")
        # get manifest remotely
        # pull x86 part
        # pull ppc part
        super(MultiArchImage, self).pull()

    def check_status(self, locally=False, remotely=False):
        missing_remotely = []
        missing_locally = []
        status_x86 = self.x86_image.check_status()
        if self.ppc_image is not None:
            status_ppc = self.ppc_image.check_status()
        if remotely:
            if self.schema == "v2_s2":
                self.api_client.manifest_exists()
            else:
                missing_remotely += status_x86['missing_remotely']
                missing_remotely += status_ppc['missing_remotely']

        if locally:
            if status_x86['missing_locally'] and status_ppc['missing_locally']:
                missing_locally += status_x86['missing_locally']
                missing_locally += status_ppc['missing_locally']

        # check multiarch
        # check_x86 in manifest
        # check_ppc in manifest
        # check x86 image
        # check ppc image

    def retag(self):
        self.x86_image.retag()
        if self.ppc_image is not None:
            self.ppc_image.retag()
        if self.schema == "v2_s2":
            super(MultiArchImage, self).retag()

    def push(self):
        self.x86_image.push
        if self.ppc_image is not None:
            self.ppc_image.push
        if self.schema == "v2_s2":
            manifest = self.create_manifest_list()
            self.api_client.manifest_put(manifest)


class SingleArchImage(RegistryImage):

    def get_image(self):
        if self.physical_image is None:
            self.get_local_image()
        if self.physical_image is None:
            self.pull()
        if self.physical_image is None:
            raise Exception("Image not found locally or remotely")

    def get_local_image(self):
        if not self.physical_image:
            try:
                self.physical_image = self.images_client.get(self.name.full)
            except docker.errors.ImageNotFound:
                pass

        return self.physical_image

    def __eq__(self, other):
        physical_image = self.get_local_image()
        digest = None
        try:
            digest = physical_image.attrs["ContainerConfig"]["Image"]
        except (KeyError, AttributeError):
            pass

        other_physical_image = other.get_local_image()
        other_digest = None
        try:
            other_digest = other_physical_image.attrs["ContainerConfig"][
                "Image"]
        except (KeyError, AttributeError):
            pass

        if digest is None and other_digest is None:
            return False
        return digest == other_digest

    def sync(self):
        manifest = self.api_client.manifest_get()
        if self.digest == manifest.digest:
            self.pull()

    def remote_compare(self, other_tag):
        if not (self.api_client.manifest_exists(self.name.full, self.name.tag)
               and self.api_client.manifest_exists(repo, other_tag)):
           return False

    def local_compare(self, other_tag):
        other = self.__class__((self.name.registry,
                                self.name.namespace,
                                self.name.base_name, other_tag),
                               self.api_client)
        return self == other

    def exists_locally(self):
        return bool(self.get_local_image())

    def exists_remotely(self):
        return self.api_client.manifest_exists(self.name.base_namespace,
                                               self.name.tag)

    def check_status(self, locally=True, remotely=False, compare_tag=None):
        status = {}
        if locally and not self.exists_locally():
            status['missing_locally'] = {self}
        if remotely and not self.exists_remotely():
            status['missing_remotely'] = {self}
        if compare_tag and self.local_compare(compare_tag):
            status['digest_mismatch'] = {self}

        return status

    def local_remove(self):
        try:
            self.images_client.remove(self.name.full, force=True)
        except docker.errors.ImageNotFound:
            pass

        self.physical_image = None

    def remote_remove(self):
        pass

    def push(self):
        self.log.debug("Pushing image %s", self.name.full)
        try:
            status_messages = self.images_client.push(self.name.full_no_tag,
                                                      tag=self.name.tag,
                                                      stream=True,
                                                      decode=True)
        except docker.errors.APIError:
            self.log.error("Error pushing")
            raise

        for status in status_messages:
            if 'error' in status:
                self.log.error("Error while pushing %s: %s", self.name.full,
                               status['error'])

                raise Exception("Push failed")
        self.log.debug("Image %s pushed successfully", self.name.full)

    def rename(self, registry, namespace, base_name, tag, locally=False,
               remotely=False):
        image = self.__class__((registry, namespace, base_name, tag),
                               self.api_client)
        if locally:
            self.physical_image.tag(image.name.full)
        if remotely:
            pass

        return image
