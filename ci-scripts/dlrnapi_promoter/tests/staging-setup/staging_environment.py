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
        self.stage_id = self.config['env-id']
        self.docker_client = docker.from_env()

    def setup_images(self, meta):
        try:
            os.mkdir(self.overcloud_images_base_dir)
            self.log.debug("Created top level images dir %s", self.overcloud_images_base_dir)
        except OSError:
            pass
        meta['dirs'].add(self.overcloud_images_base_dir)

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

    def setup_containers(self, meta):

        # Containers
        source_base_image = self.config['containers']['source_image']
        registry_data = self.docker_client.images.get_registry_data(source_base_image)
        source_image = registry_data.pull(platform="x86_64")
        base_image_registry = self.config['containers']['target_registry_url']
        images = {}
        tags = []

        tags.append(self.full_hash)
        for arch in ['ppc64le','x86_64']:
            tags.append("{}_{}".format(self.full_hash, arch))

        for distro in self.config['distros']:
            images[distro] = []
            for image_name in self.config['containers']['target_images']:
                target_image_name = "promoter-staging-{}-{}-{}".format(distro, image_name, self.stage_id)
                for tag in tags:
                    full_image = "{}/{}".format(base_image_registry, target_image_name)
                    images[distro].append((full_image, tag))
                    meta['containers'].append("{}:{}".format(full_image, tag))


        for distro, images_list in images.items():
            for image, tag in images_list:
                self.log.debug("Pushing container %s:%s", image, tag)
                source_image.tag(image, tag=tag)
                #self.docker_client.images.push(image, tag=tag)

        return images


    def generate_yaml_file(self, images, meta):
        base_dir = os.path.join(self.config['root-dir'], self.config['containers']['overcloud_containers_yaml_base_dir'])
        try:
            os.mkdir(base_dir)
        except OSError:
            pass
        meta['dirs'].add(base_dir)

        for distro, image_list in images.items():
            hash_dir = os.path.join(base_dir, distro, self.full_hash)
            try:
                os.makedirs(hash_dir)
            except OSError:
                pass

            container_file = os.path.join(hash_dir, "overcloud_containers.yaml.j2")

            image_set = set()
            for repo_name, tag in image_list:
                repo, image_name = repo_name.split("/")
                image_set.add(image_name)

            with open(container_file, 'w') as yf:
                for image_name in image_set:
                    # Tryed to serialize this directly into yaml, but the dumper adds a \n after
                    # the name_suffix part for some strange reason
                    line = "- imagename: {{ name_prefix }}%s{{ name_suffix }}\n" % (image_name)
                    yf.write(line)


    def setup_repo_path(self):
        # Setting up repo path is optional
        # dlrn hash promoted via api just create a broken link
        # but we don't care.
        repo_path = "/tmp/delorean"

        os.mkdir(repo_path + dlrn_hash)
        os.symlink(repo_path + dlrn_hash, candidate_name)

    def prepare_environment(self, meta):
        self.setup_images(meta)
        images = self.setup_containers(meta)
        self.generate_yaml_file(images, meta)
        #self.setup_repo_path()


class StagedEnvironment(object):

    log = logging.getLogger("promoter-staging")

    def __init__(self, config, env_id=None):
        self.config = config
        date = datetime.datetime.now()
        if env_id is None:
            env_id = date.strftime("%Y%m%d-%H%M%S-%f")

        self.config['env-id'] = env_id

        #self.config['base-dir']

        self.overcloud_images_base_dir = os.path.join(self.config['root-dir'], self.config['overcloud_images_base_dir'])
        self.stages = {}
        fixture_file = self.config['db_fixtures']
        self.fixture_file = fixture_file
        with open(self.fixture_file) as ff:
            self.fixture = yaml.safe_load(ff)

        for commit in self.fixture["commits"]:
            stage = StagedHash(self.config, commit["commit_hash"], commit["distro_hash"])
            self.stages[stage.full_hash] = stage

        self.meta = {}
        self.meta_file = os.path.join(self.config['root-dir'], "meta.yaml")
        self.docker_client = docker.from_env()

    def promote_overcloud_images(self, full_hash, candidate_name):
        staged_hash = self.stages[full_hash]
        staged_hash.promote_overcloud_images(candidate_name)

    def inject_dlrn_fixtures(self):
        session = dlrn_db.getSession("sqlite:///%s" % self.config['db_filepath'])
        utils.loadYAML(session, self.config['db_fixtures'])

    def setup(self):
        try:
            os.mkdir(self.config['root-dir'])
        except OSError:
            pass

        self.meta['dirs'] = set()
        self.meta['containers'] = []

        self.inject_dlrn_fixtures()
        for full_hash, stage in self.stages.items():
            stage.prepare_environment(self.meta)

        # The first commit in the fixture will be the one faking
        # a tripleo-ci-config promotion
        candidate_commit = self.fixture['commits'][0]
        candidate_full_hash = get_full_hash(candidate_commit['commit_hash'], candidate_commit['distro_hash'])
        self.promote_overcloud_images(candidate_full_hash, self.config['candidate_name'])

        with open(self.meta_file, 'w') as yf:
            yaml.dump(self.meta, stream=yf)


    def teardown(self):
        # We don't cleanup fixtures from the db
        # remove the db file is cleaner and quicker
        # as we don't create it, we don't remove it
        # a shell command will just have to remove it
        try:
            with open(self.meta_file) as mf:
                self.meta = yaml.full_load(mf)
        except IOError:
            self.log.error("No meta inform for deletion")
            raise

        self.cleanup_containers(self.meta)

        for directory in self.meta['dirs']:

            try:
                self.log.debug("removing %s", directory)
                shutil.rmtree(directory)
            except OSError:
                self.log.error("Error removing directory")
                raise



        os.unlink(self.meta_file)

    def cleanup_containers(self, meta):

        for image in meta['containers']:
            # remove container remotely
            # TODO
            # remove containers locally
            #get_registry_data()
            #curl -v -X DELETE http://registryhost:reigstryport/v2/${docker_image_name}/manifests/${digest}
            self.log.info("removing container %s", image)
            self.docker_client.images.remove(image)


def main():

    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger("promoter-staging")
    log.setLevel(logging.DEBUG)


    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('action', choices=['setup', 'teardown'])
    parser.add_argument('--env-id', default=None)
    args = parser.parse_args()

    base_path = os.path.dirname(os.path.abspath(__file__))

    config_file = os.path.join(base_path, "stage-config.yaml")
    with open(config_file) as cf:
        config = yaml.safe_load(cf)


    config['db_fixtures'] = os.path.join(base_path ,"fixtures" ,"scenario-1.yaml")
    config['db_filepath'] = os.path.join(os.environ['HOME'], "sqlite.commits")

    staged_env = StagedEnvironment(config, env_id=args.env_id)
    if args.action == 'setup':
        staged_env.setup()
    elif args.action == 'teardown':
        staged_env.teardown()

if __name__ == "__main__":
    main()
