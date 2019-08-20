"""
This script emulates the state of the environment around promoter as it would be
just before starting a promotion process.

The promotion interacts with:
    - dlrn_api (staged locally as standalone service)
    - docker registries (not staged locally)
    - images server (staged locally as normal sftp via ssh)

So this provisioner should produce

- A database usable by dlrnapi that contains hashes, users, votes from jobs
- A hierarchy for overcloud images, so image promotion script can
  sftp to localhost and change the links accordingly
  see the overcloud_images subtree in sample/tree.txt
- A hierarchy for the overcloud_containers_yaml file, passed to container-push
  playbook as a list of containers to promote see the
  overclooud_contaienrs_yaml subtree in sample/tree.txt
- A set of images to push to source registry, so the promoter has the container
  to pull and  push during the promotion run see sample/docker_images.txt
- A meta.yaml file used to cleanup any local and remote configuration,
  including local subtrees and local/remote containers see sample/meta.yaml
- A staging_environment.ini with criteria to pass to the promoter server.
  TODO(marios) remove this bit it is moved now different review ^

The tests for this script should at least check that the script produces all
the elements consistently with the samples
"""
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
    """
    This class orchestrates the various actions needed to emulate a promotion
    environment per hash. Each hash needs a set of images and containers.
    """

    log = logging.getLogger("promoter-staging")

    def __init__(self, config, commit_hash, distro_hash):
        self.config = config
        self.commit_hash = commit_hash
        self.distro_hash = distro_hash
        self.images_dirs = {}
        self.full_hash = get_full_hash(self.commit_hash, self.distro_hash)
        self.repo_path = "{}/{}/{}".format(
            commit_hash[:2], commit_hash[2:2], self.full_hash)
        self.overcloud_images_base_dir = os.path.join(
            self.config['root-dir'], self.config['overcloud_images_base_dir'])
        self.stage_id = self.config['env-id']
        self.docker_client = docker.from_env()

    def setup_images(self, meta):
        """
        For each hash, configure the images server i.e. configure local paths
        for the sftp client to promote. Paths created here mimic the hierarchy
        used by the actual images server. It also injects a single empty image
        in the path. Might consider removing as the promoter cares only about
        directories and links
        """
        try:
            os.mkdir(self.overcloud_images_base_dir)
            self.log.debug("Created top level images dir %s",
                           self.overcloud_images_base_dir)
        except OSError:
            pass
        meta['dirs'].add(self.overcloud_images_base_dir)

        for distro in self.config['distros']:
            image_dir = os.path.join(self.overcloud_images_base_dir, distro,
                                     self.config['release'], "rdo_trunk")
            self.log.info("Create image dir %s", image_dir)
            os.makedirs(os.path.join(image_dir, self.full_hash))
            image_path = os.path.join(image_dir, self.full_hash,
                                      "{}-image.tar.gz".format(self.full_hash))
            # This emulates a "touch" command
            self.log.info("Create empty image in %s", image_path)
            with open(image_path, 'w'):
                pass
            self.images_dirs[distro] = image_dir

    def promote_overcloud_images(self, candidate_name):
        """
        This function just creates a link to the images directory
        to emulate the existing links that need to be shifted when the real
        promotion happens
        """
        for distro in self.config['distros']:
            target = os.path.join(self.images_dirs[distro], self.full_hash)
            link = os.path.join(
                self.images_dirs[distro], self.config['candidate_name'])
            self.log.info("Link %s to %s as it was promoted to %s", target,
                          link, self.config['candidate_name'])
            os.symlink(target, link)

    def setup_containers(self, meta):
        """
        This sets up the container both locally and (TODO) remotely.
        it create a set of containers as defined in the stage-config file
        Duplicating per distribution available
        """

        # Containers
        source_base_image = self.config['containers']['source_image']
        registry_data = self.docker_client.images.get_registry_data(
            source_base_image)
        source_image = registry_data.pull(platform="x86_64")
        base_image_registry = self.config['containers']['target_registry_url']
        images = {}
        tags = []

        tags.append(self.full_hash)
        for arch in ['ppc64le', 'x86_64']:
            tags.append("{}_{}".format(self.full_hash, arch))

        for distro in self.config['distros']:
            images[distro] = []
            for image_name in self.config['containers']['target_images']:
                target_image_name = "promoter-staging-{}-{}-{}".format(
                                            distro, image_name, self.stage_id)
                for tag in tags:
                    full_image = "{}/{}".format(
                        base_image_registry, target_image_name)
                    images[distro].append((full_image, tag))
                    meta['containers'].append("{}:{}".format(full_image, tag))

        # (TODO)Tag and push containers remotely
        for distro, images_list in images.items():
            for image, tag in images_list:
                self.log.debug("Pushing container %s:%s", image, tag)
                source_image.tag(image, tag=tag)
                # self.docker_client.images.push(image, tag=tag)

        return images

    def generate_yaml_file(self, images, meta):
        """
        The container-push playbook of the real promoter gets a list of
        containers from a static position in a tripleo-common repo in a file
        called overcloud_containers.yaml.j2. Instead we must generate and pass
        to the promoter a file containing a limited subset of the containers
        with arbitrary names. This function generates the relevant part of the
        file using the created containers, ready for passing to promoter logic
        """
        base_dir = os.path.join(
            self.config['root-dir'],
            self.config['containers']['overcloud_containers_yaml_base_dir'])
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

            container_file = os.path.join(
                hash_dir, "overcloud_containers.yaml.j2")

            image_set = []
            for repo_name, tag in image_list:
                repo, image_name = repo_name.split("/")
                if image_name not in image_set:
                    image_set.append(image_name)

            with open(container_file, 'w') as yf:
                for image_name in image_set:
                    # Tried to serialize this directly into yaml, but the
                    # dumper adds \n after name_suffix part for some reason
                    # The only part the container-push playbook is interested
                    # in is the one between the two prefixes, that's the only
                    # part that we are putting on the file
                    line = ("- imagename: {{ name_prefix }}%s"
                            "{{ name_suffix }}\n" % (image_name))
                    yf.write(line)

    def setup_repo_path(self):
        """
        This function should setup the repo path for the dlrnapi server
        emulating the path created during the build of a repo associated
        to an hash
        But AFAIU the dlrnapi server doesn't care if directory created or not,
        the promotion via dlrnapi will create a broken link to a directory that
        doesn't exist, but doesn't produce any error. Unless we hit some error
        we can completely ignore this part and remove this TODO(panda)
        """
        # Setting up repo path is optional
        # dlrn hash promoted via api just create a broken link
        # but we don't care.
        repo_path = "/tmp/delorean"
        # TODO(fixme) if we want to keep this we must pass dlrn_hash and
        # candidate name
        dlrn_hash = "foo"
        candidate_name = "bar"
        os.mkdir(repo_path + dlrn_hash)
        os.symlink(repo_path + dlrn_hash, candidate_name)

    def prepare_environment(self, meta):
        """
        Orchestrator for the single stage component setup
        """
        self.setup_images(meta)
        images = self.setup_containers(meta)
        self.generate_yaml_file(images, meta)
        # self.setup_repo_path()


class StagedEnvironment(object):
    """
    This class drives the top level staging parts:
        - inject the fixtures for the dlrnapi database
        - orchestrates the actions from the StagedHash class
        - chooses which dlrn hash to link in the images hierarchy
          as candidate and previous-promoted for the imminent promotion
          (the counterpart in dlrnapi for this is in the fixture)
        - cleans up everything produced using the meta.yaml file
    """

    log = logging.getLogger("promoter-staging")

    def __init__(self, config, env_id=None):
        self.config = config
        date = datetime.datetime.now()
        if env_id is None:
            env_id = date.strftime("%Y%m%d-%H%M%S-%f")

        self.config['env-id'] = env_id

        # self.config['base-dir']

        self.overcloud_images_base_dir = os.path.join(
            self.config['root-dir'], self.config['overcloud_images_base_dir'])
        self.stages = {}
        fixture_file = self.config['db_fixtures']
        self.fixture_file = fixture_file
        with open(self.fixture_file) as ff:
            self.fixture = yaml.safe_load(ff)

        for commit in self.fixture["commits"]:
            stage = StagedHash(
                self.config, commit["commit_hash"], commit["distro_hash"])
            self.stages[stage.full_hash] = stage

        self.meta = {}
        self.meta_file = os.path.join(self.config['root-dir'], "meta.yaml")
        self.docker_client = docker.from_env()

    def promote_overcloud_images(self, full_hash, candidate_name):
        """
        Creates the links for the images hierarchy
        TODO: create the previous-* links
        """
        staged_hash = self.stages[full_hash]
        staged_hash.promote_overcloud_images(candidate_name)

    def inject_dlrn_fixtures(self):
        """
        Injects the fixture to the database using the existing utils
        offered by dlrn itself
        """
        session = dlrn_db.getSession(
            "sqlite:///%s" % self.config['db_filepath'])
        utils.loadYAML(session, self.config['db_fixtures'])

    def setup(self):
        """
        Orchestrates the setting up of the environment
        """
        try:
            os.mkdir(self.config['root-dir'])
        except OSError:
            pass

        # The meta data structure will contain information on what to remove
        # during teardown
        self.meta['dirs'] = set()
        self.meta['containers'] = []

        self.inject_dlrn_fixtures()

        # Use the dlrn hashes defined in the fixtures to setup all
        # the needed component per-hash
        for full_hash, stage in self.stages.items():
            stage.prepare_environment(self.meta)

        # The first commit in the fixture will be the one faking
        # a tripleo-ci-config promotion
        candidate_commit = self.fixture['commits'][0]
        candidate_full_hash = get_full_hash(
            candidate_commit['commit_hash'], candidate_commit['distro_hash'])
        self.promote_overcloud_images(
            candidate_full_hash, self.config['candidate_name'])

        # Meta output depends on structures (sets) that don't maintain order
        # This part makes meta output a bit more consistent
        # So comparing it with the existing sample will be possible
        self.meta['containers'] = sorted(self.meta['containers'])
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

        # Use information from meta file to clean up the environment
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
            # get_registry_data()
            # curl -v -X DELETE
            # http://host:port/v2/${image_name}/manifests/${digest}
            self.log.info("removing container %s", image)
            self.docker_client.images.remove(image)


def load_config(db_filepath=None):
    """
    This loads the yaml configuration file containing information on paths
    and distributions to stage
    Also adds some static informations
    """

    base_path = os.path.dirname(os.path.abspath(__file__))

    config_file = os.path.join(base_path, "stage-config.yaml")
    with open(config_file) as cf:
        config = yaml.safe_load(cf)

    if db_filepath is None:
        db_filepath = os.path.join(os.environ['HOME'], "sqlite.commits")

    config['db_fixtures'] = os.path.join(
        base_path, "fixtures", "scenario-1.yaml")
    config['db_filepath'] = db_filepath

    return config


def main():

    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger("promoter-staging")
    log.setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('action', choices=['setup', 'teardown'])
    # the env-id is used to make the code reentrant
    # so each run will have a unique identifier when pushing
    # container in the shared registry, and won't step on
    # each other's toes
    parser.add_argument('--env-id', default=None)
    args = parser.parse_args()

    config = load_config()

    staged_env = StagedEnvironment(config, env_id=args.env_id)
    if args.action == 'setup':
        staged_env.setup()
    elif args.action == 'teardown':
        staged_env.teardown()


if __name__ == "__main__":
    main()
