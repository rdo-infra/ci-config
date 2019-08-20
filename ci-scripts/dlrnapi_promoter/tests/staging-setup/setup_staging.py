from dlrn import db as dlrn_db
from dlrn import utils
import datetime
import docker
import yaml
import os
import pprint


config = {
    "distros": [
        "centos7",
        "redhat8"
    ],
    "releases": [
        "master",
        "stein"
    ],
    "overcloud_images": {
        "root":
        ""
    },
    "containers":{
        "registry_url": ""
        "template_dir": ""
    },
}


class StagedHash(object):

    def __init__(self, config, commit_hash, distro_hash):
        self.commit_hash = commit_hash
        self.distro_hash = distro_hash
        self.full_hash = "{}_{}".format(commit, distro[:8])
        self.images_paths = {}

    def setup_images(self):
        for distro in config['distros']:
            for releases in config['releases']:
                distro_dir = "{}/{}".format(distro,release)
                images_dir = "{}/{}/rdo_trunk/{}".format(config['images_root'], distro_dir, self full_hash)
                image_path = "{}/{}-image.tar.gz".format(images_dir, self.full_hash)
                self.images_paths[distro_dir] = images_dir
                os.makedirs(images_dir)
                with open(image_path, 'a'):
                    pass
            os.symlink()

    def setup_containers(self):
        self.container_suffix = "-{}".format(stage_id)

        # Containers
        client = docker.from_env()

        for image in images:
            image = client.image.pull()
            tag = image_name:new_tag
            image.tag(name, tag)
            image.push(image_new_tag)

    def generate_ooo_common_containers_file(self):
        for distro in config:
            for release in config
                container_files = "{}/{}-{}-overcloud_containers.yaml.j2".format(self.config["container_file_dir"], distro, release)
                containers = []
                for image_name in images:
                    image_spec_name = "{{ name_prefix }}{}{{ name_suffix }}".format(image_name)
                    image_spec = { "imagename": image_spec_name }
                    containers.append(image_spec)

                yaml.dump(containers_file)

    def setup_repo_path(self):
        repo_path = /tmp/delorean

        os.mkdir(repo_path + dlrn_hash)
        os.symlink(repo_path + dlrn_hash, candidate_name)

    def prepare_environemnt(self):
        self.setup_images()
        self.setup_containers()
        self.generate_ooo_common_containers_file()
        self.setup_repo_path()

class StagedEnvironment(object):

    def __init__(self, fixture_file):
        self.fixture_file = fixture_file
        with open(self.fixture_file) as ff:
            fixture = yaml.safe_load(ff)
        date = datetime.datetime.now()
        self.stage_id = date.strftime("%Y%m%d-%H%M%S-%f")
        self.containers_file = "/tmp/containers_file"

    for commit in fixture["commits"]:
        stage = StagedHash(commit["commit_hash"], commit["distro_hash"])
        stages[stage.full_hash] = stage

    def inject_dlrn_fixtures():
        session = dlrn_db.getSession("sqlite:///%s" % filepath)
        utils.loadYAML(session, 'fixtures/scenario-1.yaml')

    def setup(self):
        self.inject_dlrn_fixtures()
        for stage in stages:
            stage.setup()

    def cleanup_containers(self, containers_file):
        #get_registry_data()
        #curl -v -X DELETE http://registryhost:reigstryport/v2/${docker_image_name}/manifests/${digest}
        pass


def main():

    IMAGES_HOME="/tmp/"
    #IMAGES_HOME=os.environ.get('HOME', "/tmp")
    FIXTURE_FILE="fixtures/scenario-1.yaml"
    staged_env = StagedEnvironment(FIXTURE_FILE)
    staged_env.setup()
