from dlrn import db as dlrn_db
from dlrn import utils
import logging
import datetime
import docker
import yaml
import os
import pprint
import shutil


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
        date = datetime.datetime.now()
        self.stage_id = date.strftime("%Y%m%d-%H%M%S-%f")
        self.overcloud_images_base_dir = self.config['overcloud_images']['base_dir']

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
        self.container_suffix = "-{}".format(stage_id)

        # Containers
        client = docker.from_env()

        for image in images:
            image = client.image.pull()
            #tag = image_name:new_tag
            #image.tag(name, tag)
            #image.push(image_new_tag)

    def generate_ooo_common_containers_file(self):
        for distro in config:
            for release in config:
                container_files = "{}/{}-{}-overcloud_containers.yaml.j2".format(self.config["container_file_dir"], distro, release)
                containers = []
                for image_name in images:
                    image_spec_name = "{{ name_prefix }}{}{{ name_suffix }}".format(image_name)
                    image_spec = { "imagename": image_spec_name }
                    containers.append(image_spec)

                yaml.dump(containers_file)

    def setup_repo_path(self):
        # Setting up repo path is optional
        # dlrn hash promoted via api just create a broken link
        # but we don't care.
        repo_path = "/tmp/delorean"

        os.mkdir(repo_path + dlrn_hash)
        os.symlink(repo_path + dlrn_hash, candidate_name)

    def prepare_environment(self):
        self.setup_images()
        #self.setup_containers()
        #self.generate_ooo_common_containers_file()
        #self.setup_repo_path()

    def teardown_environment(self):
        pass

class StagedEnvironment(object):

    log = logging.getLogger("promoter-staging")

    def __init__(self, staging_config):
        self.config = staging_config
        self.containers_file = "/tmp/containers_file"
        self.overcloud_images_base_dir = self.config['overcloud_images']['base_dir']
        self.stages = {}
        fixture_file = self.config['db_fixtures']
        self.fixture_file = fixture_file
        with open(self.fixture_file) as ff:
            self.fixture = yaml.safe_load(ff)

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
