import logging
import docker
import re

from docker_clients import DockerRegistryApiClient, DockerClient


class ImageName(object):

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
            parts = ['registry', 'namespace', 'base_name',
                          'tag']

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

class BaseImage(object):

    log = logging.getLogger("promoter")

    def __init__(self, name, images_client_class=DockerClient,
                 api_client_class=DockerRegistryApiClient):
        self.name = ImageName(name)
        self.images_client = images_client_class()
        self.physical_image = None
        self.api_client = api_client_class()
        self.status = {
            'missing_locally': True,
            'missing_remotely': True
        }


    def __str__(self):
        return self.name.full

    def pull(self, platform):
        try:
            self.physical_image = self.images_client.pull(
                self.name.full_no_tag,
                tag=self.name.tag)
        except docker.errors.ImageNotFound:
            self.log.error("No image associated with this repo")
            raise

    def retag(self, dest_tag, locally=True, remotely=False):
        if locally:
            self.local_retag(dest_tag)
        if remotely:
            self.remote_retag(dest_tag)

    def local_retag(self, new_tag):
        self.get_image()
        self.image.tag(self.full_name_no_tag, new_tag)
        new_container = Image(self.registry, self.namespace,
                              self.name, new_tag)
        return new_container

    def remote_retag(self, new_tag):
        manifest = self.registry_client.manifest_get(self.full_name_no_tag,
                                                     self.tag)
        self.registry_client.manifest_post(manifest, self.full_name_no_tag,
                                           new_tag)


class MultiArchImage(BaseImage):

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

        manifest = self.manifest_get(repo, tag)
        other_manifest = self.manifest_get(repo, other_tag)
        digest = manifest['config']['digest']
        other_digest = other_manifest['config']['digest']

        return digest == other_digest

    def create_manifest(self):
        # docker python does not support multiarch manifests ....
        # push x86
        # push ppc
        # push manifest list.

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

    def check_status(self):
        self.x86_image.check_status
        if self.ppc_image is not None:
            self.ppc_image.check_status
        if remotely:
            if self.schema == "v2_s2":
                self.api_client.manifest_exists()
            else:
                missing_remotely += status_x86['missing_remotely']
                missing_remotely += status_ppc['missing_remotely']

        if locally:
            if status_x86['missing_locally'] and status_ppc['missing_locally']
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

    def push(self)
        self.x86_image.push
        if self.ppc_image is not None:
            self.ppc_image.push
        if self.schema == "v2_s2":
            manifest = self.create_manifest_list()
            self.api_client.manifest_put(manifest)


class SingleArchImage(BaseImage):


    def get_image(self):
        if self.image is None:
            self.get_local_image()
        if self.image is None:
            self.pull()
        if self.image is None:
            raise Exception("Image not found locally or remotely")

    def get_local_image(self):
        if not self.physical_image:
            try:
                self.physical_image = self.images_client.get(self.full_name)
            except docker.errors.ImageNotFound:
                pass

        return self.physical_image


    def __eq__(self, other):
        physical_image = self.get_local_image()
        digest = None
        try:
            digest = physical_image.attrs["ContainerConfig"]["Image"]
        except KeyError:
            pass

        other_physical_image = other.get_local_image()
        other_digest = None
        try:
            other_digest = other_physical_image.attrs["ContainerConfig"][
                "Image"]
        except KeyError:
            pass

        if digest is None and other_digest is None:
            return False
        return digest == other_digest

    def sync(self):
        manifest = self.api_client.manifest_get()
        if self.digest == manifest.digest:
            self.pull()

    def local_compare(self, other_tag):
        if not (self.api_client.manifest_exists(self.full, self.tag)
                and self.manifest_exists(repo, other_tag)):
            return False

        other = self.__class__((self.name.registry,
                                self.name.namespace,
                                self.name.base_name, other_tag))
        return self == other

    def exists_locally(self):
        return bool(self.get_local_image(self))

    def exists_remotely(self):
        return self.api_client.manifest_exists(self.name.full_no_tag,
                                               self.name.tag)

    def check_status(self, locally=True, remotely=False, tag=None):
        missing_locally = None
        missing_remotely = None
        different_locally = None
        if locally and not self.exists_locally():
            missing_locally = [self.name.full]
        if remotely and not self.exists_remotely():
            missing_remotely = [self.name.full]
        if tag and self.local_compare(tag):
            different_locally = [self.name.full]

        status = {
            'missing_locally': missing_locally,
            'missing_remotely': missing_remotely,
            'different_locally': different_locally,
        }

        return status

    def local_remove(self):
        try:
            self.client.images.remove(self.full_name, force=True)
        except docker.errors.ImageNotFound:
            pass

        self.physical_image = None

    def remote_remove(self):
        pass

    def push(self):
        try:
            self.images_client.push(self.name.full_no_tag, tag=self.name.tag)
        except docker.errors.APIError:
            self.log.error("Error pushing")
            raise

    def rename(self, locally=False, remotely=False):
        self.name.change()
        if locally:
            self.image.tag(self.name)
        if remotely:
            pass

class ImageList(object):
    def __init__(self, registry, namespace, tag, images=None):
        self.images = set()
        self.tag = tag
        self.namespace = namespace
        self.registry = registry
        if images is not None:
            self.add_images(images)
        self.status = {
            'missing_locally': self.images,
            'missing_remotely': self.images,
            'digest_mismatch': self.images,
        }

    def add_images(self, images):
        if isinstance(images, ImageList):
            images_list = images
            images = images_list.images
        if not isinstance(images, list) or not isinstance(images, set):
            images = [images]
        for image in images:
            if isinstance(image, str):
                base_name = image
                image = self.image_class(self.registry, self.namespace,
                                         base_name, self.tag)
            elif isinstance(image, self.image_class):
                image = image.rename(self.registry, self.namespace, None, None)

            self.images.add(image)

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

    def push(self, remove_from_list=false):
        pushed_images = []
        if remove_from_list:
            images_list = self.images
        else:
            images_list = copy.copy(self.images)
        while not images_list:
            image = images_list.pop()
            image.push()
            pushed_images.append(image)

        return pushed_images

    def pull(self, remove_from_list=false):
        pulled_images = []
        if remove_from_list:
            images_list = self.images
        else:
            images_list = copy.copy(self.images)
        while not images_list:
            image = images_list.pop()
            image.pull()
            pulled_images.append(image)

        return pulled_images


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

    def check_status(self, locally=True, remotely=False, tag=None):
        missing_locally = []
        missing_remotely = []
        digest_mismatch = []
        for image in self.images:
            status = image.check_images_status(locally=locally, remotely=remotely,
                                               tag=tag)
            missing_locally += status['missing_locally']
            missing_remotely += status['missing_remotely']
            digest_mismatch += status['digest_mismatch']

        if not locally:
            missing_locally = None
        if not remotely:
            missing_remotely = None
        self.status = {
            'missing_locally': missing_locally,
            'missing_remotely': missing_remotely,
            'digest_mismatch': digest_mismatch,
        }

        return self.status

