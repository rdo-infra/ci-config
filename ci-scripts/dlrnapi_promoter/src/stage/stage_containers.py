"""
This file contains classes to stage containers in registry at the moment
immediately before a promotion.
"""

import copy
import logging
import os
import shutil
import tempfile

import docker
import yaml
from promoter.dlrn_hash import DlrnHash

# template that emulates the tripleo-common/overcloud_containers.yaml
# definitions
containers_template = '''
container_images:

- imagename: "docker.io/tripleomaster/centos-binary-neutron-server:current-tripleo"
  image_source: kolla

- imagename: "docker.io/tripleomaster/centos-binary-nova-compute:current-tripleo"
  image_source: kolla
''' # noqa

# template that emulates the tripleo-common/tripleo_containers.yaml
# definitions
tripleo_containers_template = '''
container_images:

- imagename: "quay.io/tripleomaster/openstack-neutron-server:current-tripleo"
  image_source: tripleo

- imagename: "quay.io/tripleomaster/openstack-nova-compute:current-tripleo"
  image_source: tripleo
''' # noqa


class BaseImage(object):
    """
    Class to create and destroy empty container image as base for all
    emulated container images in stage
    """

    log = logging.getLogger("promoter-staging")

    def __init__(self, build_tag):
        """
        Initialize base image info
        :param build_tag: the full build tag for docker (host/image/tag)
        """
        self.client = docker.from_env()
        self.build_tag = build_tag
        self.image = None

    def build(self):
        """
        creates a temporary build directory with a placeholder, then injects
        a Dockerfile and builds it
        :return: The python-docker image definition
        """
        try:
            self.image = self.client.images.get(self.build_tag)
        except docker.errors.ImageNotFound:
            temp_dir = tempfile.mkdtemp()
            with open(os.path.join(temp_dir, "nothing"), "w"):
                pass
            with open(os.path.join(temp_dir, "Dockerfile"), "w") as df:
                df.write("FROM scratch\nCOPY nothing /\n")
            self.image, _ = self.client.images.build(path=temp_dir,
                                                     tag=self.build_tag)
            shutil.rmtree(temp_dir)

        return self.image

    def remove(self):
        self.client.images.remove(self.image.id, force=True)


class StagingContainers(object):
    """
    Class that stages the presence of tripleo container images in local
    registries
    """

    log = logging.getLogger("promoter-staging")

    def __init__(self, config):
        """
        like many inits around the code, this loads the config and create
        shortcuts for the used configuration parameters
        :param config: The global stage config
        """
        self.config = config
        self.dry_run = self.config['dry_run']
        self.docker_client = docker.from_env()
        # Select only the stagedhash with the promotion candidate
        candidate_hash_dict = \
            self.config.dlrn['promotions']['promotion_candidate']
        self.candidate_hash = DlrnHash(source=candidate_hash_dict)
        self.containers_list_base = \
            self.config.containers['containers_list_base']

        self.containers_list_exclude_config = \
            self.config.containers['containers_list_exclude_config']

        self.containers_list_path = self.config.containers[
            'containers_list_path']
        self.tripleo_commit_sha = self.config.containers['tripleo_commit_sha']
        self.source_registry = None
        for registry in self.config.registries:
            if registry['type'] == "source":
                self.source_registry = registry
                break

        if self.source_registry is None:
            raise Exception("No source registry specified in configuration")

        self.base_image = BaseImage("promotion-stage-base:v1")

        if not self.dry_run:
            self.source_image = self.base_image.build()

        self.suffixes = self.config.containers['images-suffix']
        self.distro = self.config['distro']
        self.namespace = self.config.containers['namespace']

        self.distro_name = self.config['distro_name']
        self.pushed_images = []
        self.containers_root = self.config.containers['root']
        self.excluded_containers = ['nonexisting', 'excluded']
        self.exclude_ppc_containers = ['nonppc', 'ppc_excluded']

    def setup(self):
        """
        This is the main method, sets up paths, launche base image build,
        the pushes the image multiple times with different names and tags to
        the source registry
        :return: The container stage info for the created containers
        """
        try:
            os.makedirs(self.containers_root)
        except OSError:
            pass

        tags = [self.candidate_hash.full_hash]
        for arch in ['ppc64le', 'x86_64']:
            tags.append("{}_{}".format(self.candidate_hash.full_hash, arch))

        # Don't push containers that are in the exclude list
        suffixes = copy.copy(self.suffixes)
        for excluded in self.excluded_containers:
            try:
                suffixes.remove(excluded)
            except ValueError:
                self.log.debug("Not excluding container %s", excluded)

        for image_name in suffixes:
            if self.config['release'] in ['queens', 'stein',
                                          'train', 'ussuri']:
                target_image_name = "{}-binary-{}".format(
                    self.distro_name, image_name)
            else:
                target_image_name = "openstack-{}".format(image_name)
            for tag in tags:
                image = "{}/{}".format(self.namespace, target_image_name)
                full_image = "localhost:{}/{}".format(
                    self.source_registry['port'], image)
                self.log.debug("Pushing container %s:%s"
                               " to localhost:%s",
                               image, tag, self.source_registry['port'])
                # Skip ppc tagging on the last image in the list
                # to emulate real life scenario
                if "ppc64le" in tag and image_name == self.suffixes[-1]:
                    continue
                if not self.dry_run:
                    self.source_image.tag(full_image, tag=tag)
                image_tag = "{}:{}".format(full_image, tag)

                self.pushed_images.append("{}:{}".format(image, tag))

                if self.dry_run:
                    continue

                self.docker_client.images.push(full_image, tag=tag)
                self.docker_client.images.remove(image_tag)

        if not self.dry_run:
            self.base_image.remove()

        self.generate_containers_yaml()

        return self.stage_info

    @property
    def stage_info(self):
        """
        Property that returns the stage info for the containers
        :return: The stage info for the containers subsection
        """
        stage_info = {
            'containers_list_base_url': "file://{}".format(
                self.containers_list_base),
            'containers_list_exclude_config': "file://{}".format(
                self.containers_list_exclude_config),
            'images': self.pushed_images
        }
        return stage_info

    def generate_containers_yaml(self):
        """
        The container-push playbook of the promoter gets a list of
        containers from a static position in a tripleo-common repo in a file
        called overcloud_containers.yaml or tripleo_containers.yaml.
        This method creates this file
        :return: None
        """
        if self.dry_run:
            return
        containers_list_path = \
            os.path.join(self.containers_list_base,
                         self.tripleo_commit_sha,
                         self.containers_list_path)
        try:
            os.makedirs(os.path.dirname(containers_list_path))
        except OSError:
            self.log.debug("Directory exists")
        # Current template supports only two images, 0 and 1 in our list are
        # base and openstack-base, they are hardcoded and are not needed here
        with open(containers_list_path, "w") as containers_file:
            containers_file.write(containers_template)

        # Generate tripleo_containers.yaml file
        tripleo_containers_path = \
            os.path.join(self.containers_list_base,
                         self.tripleo_commit_sha,
                         'container-images/tripleo_containers.yaml')
        with open(tripleo_containers_path, "w") as tripleo_file:
            tripleo_file.write(tripleo_containers_template)

        exclude_config = {
            'exclude_containers': {
                'master': self.excluded_containers,
                'ussuri': self.excluded_containers,
                'train': self.excluded_containers,
            },
            'exclude_ppc_containers': {
                'master': self.exclude_ppc_containers
            },
        }
        f_name = self.containers_list_exclude_config
        if self.containers_list_exclude_config.startswith("file://"):
            f_name = self.containers_list_exclude_config.split("file://")[-1]
        with open(f_name, "w") as exclude_file:
            exclude_file.write(yaml.safe_dump(exclude_config))

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

    def teardown(self, __):
        """
        This cleans up resources created by the setup.
        It just removes the root dir tree
        We don't need to teardown all the containes created. The
        containers are deleted immediately at deletion of registries
        :param __: An ignored parameter useful for other teardown methods
        :return: None
        """
        shutil.rmtree(self.containers_root)
