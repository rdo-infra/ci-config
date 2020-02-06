import docker
import logging
import os
import pprint
import tempfile
import shutil

from dlrn_interface import (DlrnCommitDistroHash, DlrnHash,
                            DlrnClient, DlrnClientConfig)


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
        self.pattern_file_path = self.config.containers['pattern_file_path']

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
        self.namespace = self.config.containers['namespace']
        self.distro = self.config.main['distro']
        self.pushed_images = []

    def setup(self):
        """
        This sets up the container both locally and remotely.
        it create a set of containers as defined in the stage-config file
        Duplicating per distribution available
        """
        tags = [self.candidate_hash.full_hash]
        for arch in ['ppc64le', 'x86_64']:
            tags.append("{}_{}".format(self.candidate_hash.full_hash, arch))

        for image_name in self.suffixes:
            target_image_name = "{}-binary-{}".format(
                self.distro, image_name)
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

        self.generate_pattern_file()

        return self.stage_info

    @property
    def stage_info(self):
        stage_info = {
            'pattern_file_path': self.pattern_file_path,
            'images': self.pushed_images
        }
        return stage_info

    def generate_pattern_file(self):
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

        with open(self.pattern_file_path, "w") as pattern_file:
            for image_name in self.suffixes:
                line = ("^{}$\n".format(image_name))
                pattern_file.write(line)

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
        os.unlink(self.pattern_file_path)
