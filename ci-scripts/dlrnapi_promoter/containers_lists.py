import logging
import docker
import re


class DockerImage(object):

    log = logging.getLogger("promoter")

    def __init__(self, registry, namespace, name, tag):
        self.client = docker.from_env()
        self.registry = registry
        self.namespace = namespace
        self.name = name
        self.tag = tag
        self.physical_image = None
        self.registry_client = registry_client

    def get_name(self, components=None):
        name = ""
        if components is None:
            components = ['registry', 'namespace', 'name',
                          'tag']

        if self.name and 'name' in components:
            name = "{}".format(self.name)
        if self.namespace and 'namespace' in components:
            name = "{}/{}".format(self.namespace, name)
        if self.registry and 'registry' in components:
            name = "{}/{}".format(self.registry, name)
        if self.tag and 'tag' in components:
            name = "{}:{}".format(name, self.tag)

        return name

    @property
    def full_name(self):
        return self.get_name()

    def __str__(self):
        return self.full_name

    def __eq__(self, other):
        
        pass

    @property
    def full_name_no_tag(self):
        return self.get_name(components=['registry', 'namespace', 'name'])

    def pull(self):
        try:
            self.physical_image = self.client.images.pull(self.full_name_no_tag,
                                                          tag=self.tag)
        except docker.errors.ImageNotFound:
            self.log.error("No image associated with this repo")
            raise

    def get_image(self):
        if self.image is None:
            try:
                self.physical_image = self.client.images.get(self.full_name)
            except docker.errors.ImageNotFound:
                self.pull()

    def local_exists(self):
        pass

    def remote_exists(self):
        self.registry_client.manifest_exists(self.full_name_no_tag, self.tag)

    def retag(self, dest_tag, local=True, remote=False):
        if local:
            self.local_retag(dest_tag)
        if remote:
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
            self.client.images.push(self.full_name_no_tag, tag=self.tag)
        except docker.errors.APIError:
            self.log.error("Error pushing")
            raise

    def repo_rename(self, repo=None, components=None, replace={},
                    parts=['registry', 'namespace', 'repo', 'tag']):
        """
        Deconstructs a repo name and reconstructrs following rules
        part of a name can be selectivley included or replaced
        """
        if repo is None and components is None:
            raise TypeError("No repo and no components specified")

        if components is None:
            components = self.get_containers_components(repo)

        components.update(replace)
        full_name = ""
        for part in parts:
            if part not in components:
                self.log.error("repo_rename: Invalid part '{}'", part)
                continue
            if part == 'registry':
                if components['registry'] is None:
                    components['registry'] = ""
                else:
                    components['registry'] += "/"

            elif part == 'tag':
                if components['tag'] is None:
                    components['tag'] = ""
                else:
                    components['tag'] = ":" + components['tag']
            elif part == 'namespace':
                if components['namespace'] is None:
                    components['namespace'] = ""
                else:
                    components['namespace'] += "/"

            full_name += components[part]

        return full_name

    def get_containers_components(self, full_name):
        ''' The regex fails in some corner cases:
            "localhost:6000/nova" (rare)
            "nova" (not rare locally)
            Both need special cases
        '''
        container_regex = (r"(\w*:[0-9]{,5})?/?([\w-]*)?/?([\w-]*):+([\w]["
                           r"\w.-]{0,127})?")
        # TODO(gcerami) For case 1 we should count the  / in the name, if we
        # have only one we are in the special case
        # For case 2 search for a / in the full_name
        if "/" not in full_name:
            components = (None, None, full_name, None)
        else:
            components = re.search(container_regex, full_name).groups()
            # create a dictionary with the components name as keys
            components = dict(zip(("registry", "namespace", "repo", "tag"),
                                  components))

        return components


class ImageList(object):
    def __init__(self, registry, namespace, tag, images=None, base_names=None):
        self._list = []
        self.tag = tag
        self.namespace = namespace
        self.registry = registry
        if images is not None:
            self.add_image_list(images)

        if base_names is not None:
            self.add_base_names_list(images)

    def add_image(self, image):
        self._list.append(image)

    def add_container_repo_list(self, images_list):
        for image in images_list:
            self.add_image(image)

    def add_base_name(self, base_name):
        image = Image(self.registry, self.namespace, base_name, self.tag)
        self._list.append(image)

    def add_base_names_list(self, base_names_list):
        for base_name in base_names_list:
            self.add_base_name(base_name)

    def local_retag(self, new_tag):
        retagged_images = []
        for repo in self._list:
            retagged_images.append(repo.local_retag(new_tag))
        new_list = ImageList(self.registry, self.namespace, self.tag,
                             images=retagged_images)
        return new_list

    def pull(self):
        for repo in self._list:
            repo.pull()

    def containers_filter(self, containers, filters):
        ''' filters is a sictionary of field:regex to apply to container
        '''
        filtered_containers = []

        # If there are no filters, everything matches
        if not filters:
            return containers

        for full_name in containers:
            components = self.get_containers_components(full_name)

            res = []
            for key, value in filters.items():
                res.append(bool(re.search(value, components[key])))
            if all(res) and res is not []:
                filtered_containers.append(full_name)

        return filtered_containers


