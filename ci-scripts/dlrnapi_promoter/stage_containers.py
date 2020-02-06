import docker
import logging
import os
import pprint
import tempfile
import shutil
from string import Template

from dlrn_interface import (DlrnCommitDistroHash, DlrnHash,
                            DlrnClient, DlrnClientConfig)

containers_template = '''
container_images_template:

- imagename: "{{namespace}}/{{name_prefix}}${image2}{{name_suffix}}:{{tag}}"
  image_source: kolla
  params:
  - ContainerAodhApiImage
  - ContainerAodhConfigImage
  services:
  - OS::TripleO::Services::AodhApi
  - OS::TripleO::Services::AodhEvaluator
  - OS::TripleO::Services::AodhListener
  - OS::TripleO::Services::AodhNotifier
  - OS::TripleO::Services::UndercloudAodhApi
  - OS::TripleO::Services::UndercloudAodhEvaluator
  - OS::TripleO::Services::UndercloudAodhListener
  - OS::TripleO::Services::UndercloudAodhNotifier

- imagename: "{{namespace}}/{{name_prefix}}${image1}{{name_suffix}}:{{tag}}"
  image_source: kolla
  params:
  - ContainerAodhEvaluatorImage
  services:
  - OS::TripleO::Services::AodhEvaluator
  - OS::TripleO::Services::UndercloudAodhEvaluator
'''


class BaseImage(object):

    log = logging.getLogger("promoter-staging")

    def __init__(self, build_tag):
        self.client = docker.from_env()
        self.build_tag = build_tag

    def build(self):
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

    log = logging.getLogger("promoter-staging")

    def __init__(self, config):
        self.config = config
        self.dry_run = self.config.main['dry_run']
        self.docker_client = docker.from_env()
        # Select only the stagedhash with the promotion candidate
        candidate_hash_dict = \
            self.config.dlrn['promotions']['promotion_candidate']
        self.candidate_hash = DlrnHash(source=candidate_hash_dict)
        self.containers_yaml = self.config.containers['containers_yaml']

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
        self.distro = self.config.main['distro']
        self.namespace = self.config.containers['namespace']

        self.distro_name = self.config.main['distro_name']
        self.pushed_images = []
        self.containers_root = self.config.containers['root']

    def setup(self):
        """
        This sets up the container both locally and remotely.
        it create a set of containers as defined in the stage-config file
        Duplicating per distribution available
        """
        try:
            os.makedirs(self.containers_root)
        except OSError:
            pass

        tags = [self.candidate_hash.full_hash]
        for arch in ['ppc64le', 'x86_64']:
            tags.append("{}_{}".format(self.candidate_hash.full_hash, arch))

        for image_name in self.suffixes:
            target_image_name = "{}-binary-{}".format(
                self.distro_name, image_name)
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
        stage_info = {
            'containers_yaml_url': "file://{}".format(self.containers_yaml),
            'images': self.pushed_images
        }
        return stage_info

    def generate_containers_yaml(self):
        """
        The container-push playbook of the real promoter gets a list of
        containers from a static position in a tripleo-common repo in a file
        called overcloud_containers.yaml.j2.
        We don't intervene in that part, and it will be tested with the rest.
        But container-push now allows for this list to match against a grep
        pattern file in a fixed position. We create such file during staging
        setup So the list of containers effectively considered will be reduced.
        """
        if self.dry_run:
            return

        # Current template supports only two images, 0 and 1 in our list are
        # base and openstack-base, they are hardcoded and are not needed here
        with open(self.containers_yaml, "w") as containers_file:
            template = Template(containers_template)
            containers_yaml_j2 = template.substitute({
                'image1': self.suffixes[-2],
                'image2': self.suffixes[-1],
            })
            containers_file.write(containers_yaml_j2)

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
        # We don't normally need to teardown all the containes created. The
        # containers
        # are deleted immediately after pushing them to the source registry
        shutil.rmtree(self.containers_root)
