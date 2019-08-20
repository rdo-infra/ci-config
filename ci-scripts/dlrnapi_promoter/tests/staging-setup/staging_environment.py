import argparse
import datetime
import docker
import logging
import os
import pprint
import shutil
import yaml

from dlrn import db as dlrn_db
from dlrn import utils


def get_full_hash(commit_hash, distro_hash):
    return "{}_{}".format(commit_hash, distro_hash[:8])


class StagedHash(object):

    log = logging.getLogger("promoter-staging")

    def __init__(self, config, commit_hash, distro_hash):
        self.config = config
        self.commit_hash = commit_hash
        self.distro_hash = distro_hash
        self.images_dirs = {}
        self.full_hash = get_full_hash(self.commit_hash, self.distro_hash)
        self.repo_path = "{}/{}/{}".format(commit_hash[:2], commit_hash[2:2], self.full_hash)
        self.overcloud_images_base_dir = os.path.join(self.config['root-dir'], self.config['overcloud_images_base_dir'])
        self.stage_id = self.config['stage-id']

    def setup_images(self):
        try:
            os.mkdir(self.overcloud_images_base_dir)
            self.log.debug("Created top level images dir %s", self.overcloud_images_base_dir)
        except OSError:
            pass
        for distro in self.config['distros']:
            image_dir = os.path.join(self.overcloud_images_base_dir, distro, self.config['release'], "rdo_trunk")
            self.log.info("Create image dir %s", image_dir)
            os.makedirs(os.path.join(image_dir, self.full_hash))
            image_path = os.path.join(image_dir, self.full_hash, "{}-image.tar.gz".format(self.full_hash))
            # This emulates a "touch" command
            self.log.info("Create empty image in %s", image_path)
            with open(image_path, 'w'):
                pass
            self.images_dirs[distro] = image_dir

    def promote_overcloud_images(self, candidate_name):
        for distro in self.config['distros']:
            target = os.path.join(self.images_dirs[distro], self.full_hash)
            link = os.path.join(self.images_dirs[distro], self.config['candidate_name'])
            self.log.info("Link %s to %s as it was promoted to %s", target, link, self.config['candidate_name'])
            os.symlink(target, link)

    def setup_containers(self):

        # Containers
        client = docker.from_env()
        source_base_image = self.config['containers']['source_image']
        registry_data = client.images.get_registry_data(source_base_image)
        source_image = registry_data.pull(platform="x86_64")
        base_image_registry = self.config['containers']['target_registry_url']
        images = {}
        tags = []

        tags.append(self.full_hash)
        for arch in ['ppc64le','x86_64']:
            tags.append("{}_{}".format(self.full_hash, arch))

        for image_name in self.config['containers']['target_images']:
            for distro in self.config['distros']:
                images[distro] = []
                image_name = "promoter-staging-{}-{}-{}".format(distro, image_name, self.stage_id)
                for tag in tags:
                    full_image = "{}/{}".format(base_image_registry, image_name)
                    images[distro].append((full_image, tag))


        for distro, images in images.items():
            for image, tag in images:
                self.log.debug("Pushing container %s:%s", image, tag)
                source_image.tag(image, tag=tag)
                #client.images.push(image, tag=tag)

        return images

    def generate_yaml_file(self, images):
        base_dir = os.path.join(self.config['root-dir'], self.config['containers']['overcloud_containers_yaml_base_dir'])
        for distro, images in images.items():
            containers = []
            yaml_file = "{}/{}-overcloud_containers.yaml.j2".format(base_dir, distro)
            for image_name, tag in images:
                image_spec_name = "{{ name_prefix }}{}{{ name_suffix }}".format(image_name)
                image_spec = { "imagename": image_spec_name }
                containers.append(image_spec)

            with open(yaml_file) as yf:
                yaml.dump(containers, stream=yf)


    def setup_repo_path(self):
        # Setting up repo path is optional
        # dlrn hash promoted via api just create a broken link
        # but we don't care.
        repo_path = "/tmp/delorean"

        os.mkdir(repo_path + dlrn_hash)
        os.symlink(repo_path + dlrn_hash, candidate_name)

    def prepare_environment(self):
        self.setup_images()
        images = self.setup_containers()
        self.generate_yaml_file(images)
        #self.setup_repo_path()

    def teardown_environment(self):
        pass

class StagedEnvironment(object):

    log = logging.getLogger("promoter-staging")

    def __init__(self, staging_config):
        self.config = staging_config
        self.containers_file = "/tmp/containers_file"
        self.overcloud_images_base_dir = os.path.join(self.config['root-dir'], self.config['overcloud_images_base_dir'])
        self.stages = {}
        fixture_file = self.config['db_fixtures']
        self.fixture_file = fixture_file
        with open(self.fixture_file) as ff:
            self.fixture = yaml.safe_load(ff)

        date = datetime.datetime.now()
        self.config['stage-id'] = date.strftime("%Y%m%d-%H%M%S-%f")
        self.config['stage-id'] = "12345"
        for commit in self.fixture["commits"]:
            stage = StagedHash(self.config, commit["commit_hash"], commit["distro_hash"])
            self.stages[stage.full_hash] = stage

    def promote_overcloud_images(self, full_hash, candidate_name):
        staged_hash = self.stages[full_hash]
        staged_hash.promote_overcloud_images(candidate_name)

    def inject_dlrn_fixtures(self):
        session = dlrn_db.getSession("sqlite:///%s" % self.config['db_filepath'])
        utils.loadYAML(session, self.config['db_fixtures'])

    def setup(self):
        self.inject_dlrn_fixtures()
        for full_hash, stage in self.stages.items():
            stage.prepare_environment()


        # The first commit in the fixture will be the one faking
        # a tripleo-ci-config promotion
        candidate_commit = self.fixture['commits'][0]
        candidate_full_hash = get_full_hash(candidate_commit['commit_hash'], candidate_commit['distro_hash'])
        self.promote_overcloud_images(candidate_full_hash, self.config['candidate_name'])

    def teardown(self):
        # We don't cleanup fixtures from the db
        # remove the db file is cleaner and quicker
        # as we don't create it, we don't remove it
        # a shell command will just have to remove it
        try:
            self.log.debug("removing %s", self.overcloud_images_base_dir)
            shutil.rmtree(self.overcloud_images_base_dir)
        except OSError:
            self.log.error("Error removing directory")
            raise

        for full_hash, stage in self.stages.items():
            stage.teardown_environment()

    def cleanup_containers(self, containers_file):
        #get_registry_data()
        #curl -v -X DELETE http://registryhost:reigstryport/v2/${docker_image_name}/manifests/${digest}
        pass


def main():

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('action', choices=['setup', 'teardown'])
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger("promoter-staging")
    logging.basicConfig(level=logging.DEBUG)

    log.setLevel(logging.DEBUG)
    base_path = os.path.dirname(os.path.abspath(__file__))

    config_file = os.path.join(base_path, "stage-config.yaml")
    with open(config_file) as cf:
        config = yaml.safe_load(cf)


    config['db_fixtures'] = os.path.join(base_path ,"fixtures" ,"scenario-1.yaml")
    config['db_filepath'] = os.path.join(os.environ['HOME'], "sqlite.commits")
    staged_env = StagedEnvironment(config)
    if args.action == 'setup':
        staged_env.setup()
    elif args.action == 'teardown':
        staged_env.teardown()

if __name__ == "__main__":
    main()
