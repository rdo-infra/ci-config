"""
This script emulates the state of the environment around promoter as it would be
just before starting a promotion process.

The promotion interacts with:
    - dlrn_api (staged locally as standalone service)
    - docker registries (staged locally with registries on different ports)
    - images server (staged locally as normal sftp via ssh)

It can setup different components independently, the list of components it
handles it's currently defined by the "components" variable

This provisioner should produce

- A database usable by dlrnapi that contains hashes, users, votes from jobs
- A hierarchy for overcloud images, so image promotion script can
  sftp to localhost and change the links accordingly
  see the overcloud_images subtree in sample/tree.txt
- A pattern file, optionally used by container-push
  playbook as a list of containers to promote see the
  overcloud_contaienrs_yaml subtree in sample/tree.txt
- a yaml file containing reusable information on what this script produced for
  the components called
- A set of images pushed to source registry, so the promoter has the container
  to pull and  push during the promotion run see sample/docker_images.txt
- A staging_environment.ini with criteria to pass to the promoter server.
  TODO(marios) remove this bit it is moved now different review ^

The tests for this script should at least check that the script produces all
the elements consistently with the samples
"""
import argparse
import docker
import logging
import os
import pprint
import shutil
import sqlite3
import tempfile
import yaml

from dlrn import db as dlrn_db
from dlrn import utils
from string import Template


def get_full_hash(commit_hash, distro_hash):
    return "{}_{}".format(commit_hash, distro_hash[:8])


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


class Registry(object):

    log = logging.getLogger("promoter-staging")

    def __init__(self, name, port=None):
        self.port = port
        self.name = name
        self.docker_client = docker.from_env()
        self.docker_containers = self.docker_client.containers
        self.docker_images = self.docker_client.images
        self.container = None
        try:
            self.container = self.docker_containers.get(name)
            self.log.info("Reusing existing registry %s", name)
        except docker.errors.NotFound:
            self.registry_image_name = "registry:2"
            # Try locally first, then contact registry
            try:
                self.registry_image = self.docker_images.get(
                    self.registry_image_name)
            except docker.errors.ImageNotFound:
                self.log.info("Downloading registry image")
                self.registry_image = self.docker_images.pull(
                    "docker.io/{}".format(self.registry_image_name))

    def run(self):
        if self.container is not None:
            return

        kwargs = {
            'name': self.name,
            'detach': True,
            'restart_policy': {
                'Name': 'always',
            },
            'ports': {
                '5000/tcp': self.port
            },
        }
        self.container = self.docker_containers.run(self.registry_image.id,
                                                    **kwargs)
        self.log.info("Created registry %s", self.name)

    def stop(self):
        if self.container is not None:
            self.container.stop()
            self.container.remove()
            self.container = None


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
        self.overcloud_images_base_dir = \
            self.config['overcloud_images']['base_dir']
        self.docker_client = docker.from_env()

    def setup_images(self):
        """
        For each hash, configure the images server i.e. configure local paths
        for the sftp client to promote. Paths created here mimic the hierarchy
        used by the actual images server. It also injects a single empty image
        in the path. Might consider removing as the promoter cares only about
        directories and links
        """
        distro_images_dir = self.config['distro_images_dir']
        image_path = os.path.join(distro_images_dir, self.full_hash,
                                  "{}-image.tar.gz".format(self.full_hash))
        self.images_dirs[self.config['distro']] = distro_images_dir

        if self.config['dry-run']:
            return

        os.mkdir(os.path.join(distro_images_dir, self.full_hash))
        # This emulates a "touch" command
        self.log.info("Create empty image in %s", image_path)
        with open(image_path, 'w'):
            pass

    def promote_overcloud_images(self, promotion_target):
        """
        This function just creates a link to the images directory
        to emulate the existing links that need to be shifted when the real
        promotion happens
        """
        distro = self.config['distro']
        target = os.path.join(self.images_dirs[distro], self.full_hash)
        link = os.path.join(
            self.images_dirs[distro], promotion_target)

        if self.config['dry-run']:
            return

        try:
            os.symlink(target, link)
            self.log.info("Link %s to %s as it was promoted to %s", target,
                          link, promotion_target)
        except OSError:
            self.log.info("Overcloud images already promoted, not creating")

    def setup_containers(self):
        """
        This sets up the container both locally and remotely.
        it create a set of containers as defined in the stage-config file
        Duplicating per distribution available
        """

        base_image = BaseImage("promotion-stage-base:v1")
        if not self.config['dry-run']:
            source_image = base_image.build()

        source_registry = None
        for registry in self.config['registries']:
            if registry['type'] == "source":
                source_registry = registry
                break

        if source_registry is None:
            raise Exception("No source registry specified in configuration")

        tags = []
        pushed_images = []
        tags.append(self.full_hash)
        for arch in ['ppc64le', 'x86_64']:
            tags.append("{}_{}".format(self.full_hash, arch))

        suffixes = self.config['containers']['images-suffix']
        namespace = self.config['containers']['namespace']
        distro = self.config['distro']
        for image_name in suffixes:
            target_image_name = "{}-binary-{}".format(
                                        distro, image_name)
            for tag in tags:
                image = "{}/{}".format(namespace, target_image_name)
                full_image = "localhost:{}/{}".format(
                    source_registry['port'], image)
                self.log.debug("Pushing container %s:%s"
                               " to localhost:%s",
                               image, tag, source_registry['port'])
                # Skip ppc tagging on the last image in the list
                # to emulate real life scenario
                if ("ppc64le" in tag and image_name == suffixes[-1]):
                    continue
                if not self.config['dry-run']:
                    source_image.tag(full_image, tag=tag)
                image_tag = "{}:{}".format(full_image, tag)

                pushed_images.append("{}:{}".format(image, tag))

                if self.config['dry-run']:
                    continue

                self.docker_client.images.push(full_image, tag=tag)
                self.docker_client.images.remove(image_tag)

        self.config['results']['containers'] = pushed_images

        if not self.config['dry-run']:
            base_image.remove()

    def setup_repo_path(self):
        """
        CANDIDATE FOR REMOVAL
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

    def prepare_environment(self):
        """
        Orchestrator for the single stage component setup
        """
        if (self.config['components'] == "all"
           or "overcloud-images" in self.config['components']):
            self.setup_images()


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

    def __init__(self, config):
        self.config = config

        self.overcloud_images_base_dir = \
            self.config['overcloud_images']['base_dir']

        distro_path = "{}{}".format(self.config['distro'],
                                    self.config['distro_version'])
        image_dir = os.path.join(self.overcloud_images_base_dir, distro_path,
                                 self.config['release'], "rdo_trunk")
        self.config['distro_images_dir'] = image_dir

        self.stages = {}
        self.registries = {}
        self.fixture_file = self.config['db_fixtures']
        with open(self.fixture_file) as ff:
            self.fixture = yaml.safe_load(ff)

        self.analyze_commits(self.fixture)

        for commit in self.config['results']['commits']:
            stage = StagedHash(
                self.config, commit["commit_hash"], commit["distro_hash"])
            self.stages[commit['full_hash']] = stage

        self.docker_client = docker.from_env()

    def promote_overcloud_images(self):
        """
        Creates the links for the images hierarchy
        TODO: create the previous-* links
        """
        for _, promotion in self.config['results']['promotions'].items():
            staged_hash = self.stages[promotion['full_hash']]
            staged_hash.promote_overcloud_images(promotion['name'])

    def inject_dlrn_fixtures(self):
        """
        Injects the fixture to the database using the existing utils
        offered by dlrn itself
        """
        session = dlrn_db.getSession(
            "sqlite:///%s" % self.config['db_filepath'])
        db_filepath = self.config['db_filepath']
        self.config['results']['inject-dlrn-fixtures'] = db_filepath
        self.config['results']['dlrn_host'] = self.config['dlrn_host']

        if self.config['dry-run']:
            return

        try:
            utils.loadYAML(session, self.config['db_fixtures'])
        except sqlite3.IntegrityError:
            self.log.info("DB is not empty, not injecting fixtures")

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
        image_names = self.config['containers']['images-suffix']
        pattern_file_path = self.config['containers']['pattern_file_path']
        self.config['results']['pattern_file_path'] = pattern_file_path

        if self.config['dry-run']:
            return

        with open(pattern_file_path, "w") as pattern_file:
            for image_name in image_names:
                line = ("^{}$\n".format(image_name))
                pattern_file.write(line)

    def setup_registries(self):
        results = {}
        for registry_conf in self.config['registries']:
            if registry_conf['type'] == "source" and "source" in results:
                continue
            if registry_conf['type'] == "source":
                results.update({
                    'source': {
                        'host': "localhost:{}".format(registry_conf['port']),
                        'name': registry_conf['name'],
                        'namespace': self.config['containers']['namespace'],
                        'username': 'unused',
                        'password': 'unused',
                    }
                })
            else:
                if "targets" not in results:
                    results['targets'] = []
                results['targets'].append({
                    'host': "localhost:{}".format(registry_conf['port']),
                    'name': registry_conf['name'],
                    'namespace': self.config['containers']['namespace'],
                    'username': 'unused',
                    'password': 'unused',
                })
            if self.config['dry-run']:
                continue

            registry = Registry(registry_conf['name'],
                                port=registry_conf['port'])
            registry.run()

        self.config['results']['registries'] = results

    def teardown_registries(self, results):
        for registry_conf in results['targets'] + [results['source']]:
            registry = Registry(registry_conf['name'])
            registry.stop()

    def setup(self):
        """
        Orchestrates the setting up of the environment
        """

        self.config['results']['release'] = self.config['release']
        self.config['results']['distro'] = self.config['distro']
        self.config['results']['distro_version'] = self.config['distro_version']
        self.config['results']['promotion_target'] = \
            self.config['promotion_target']

        template = Template(self.config['logfile_template'])
        logfile = template.substitute({
            'distro': self.config['distro'],
            'distro_version': self.config['distro_version'],
            'promoter_user': self.config['promoter_user'],
            'release': self.config['release'],
        })
        self.config['results']['logfile'] = logfile
        if (self.config['components'] == "all"
           or "registries" in self.config['components']):
            self.setup_registries()

        if (self.config['components'] == "all"
           or "inject-dlrn-fixtures" in self.config['components']):
            self.inject_dlrn_fixtures()

        if (self.config['components'] == "all"
           or "container-images" in self.config['components']):
            # Select only the stagedhash with the promotion candidate
            candidate_full_hash = \
                self.config['promotions']['promotion_candidate']['full_hash']
            self.stages[candidate_full_hash].setup_containers()
            self.generate_pattern_file()

        if (self.config['components'] == "all"
           or "overcloud-images" in self.config['components']):
            try:
                os.mkdir(self.overcloud_images_base_dir)
                self.log.debug("Created top level images dir %s",
                               self.overcloud_images_base_dir)
            except OSError:
                self.log.info("Overcloud images dir is not empty, not creating"
                              "hierarchy")

            self.config['results']['overcloud_images'] = {}
            self.config['results']['overcloud_images']['base_dir'] = \
                self.overcloud_images_base_dir
            self.config['results']['overcloud_images']['host'] = "localhost"
            self.config['results']['overcloud_images']['user'] = \
                self.config['promoter_user']

            self.config['results']['overcloud_images']['key_path'] = "unknown"

            if not self.config['dry-run']:
                self.log.info("Creating image dir %s",
                              self.config['distro_images_dir'])
                os.makedirs(self.config['distro_images_dir'])

        # Use the dlrn hashes defined in the fixtures to setup all
        # the needed component per-hash
        for full_hash, stage in self.stages.items():
            stage.prepare_environment()

        if (self.config['components'] == "all"
           or "overcloud-images" in self.config['components']):
            self.promote_overcloud_images()

        with open(self.config['stage-info-path'], "w") as stage_info:
            stage_info.write(yaml.dump(self.config['results']))

    def analyze_commits(self, fixture_data):
        commits = []
        for db_commit in fixture_data['commits']:
            commit = {
                'commit_hash': db_commit['commit_hash'],
                'distro_hash': db_commit['distro_hash'],
                'full_hash': get_full_hash(db_commit['commit_hash'],
                                           db_commit['distro_hash']),
            }
            # Find name for commit in promotions if exists
            for promotion in fixture_data['promotions']:
                if promotion['commit_id'] == db_commit['id']:
                    commit['name'] = promotion['promotion_name']
            commits.append(commit)

        self.config['results']['commits'] = commits
        # First commit is currently promoted
        currently_promoted = commits[0]
        # Second commit is currently promoted
        previously_promoted = commits[1]
        # Last commit is the promotion candidate
        promotion_candidate = commits[-1]

        self.config['promotions'] = {
            'currently_promoted': currently_promoted,
            'previously_promoted': previously_promoted,
            'promotion_candidate': promotion_candidate,
        }
        self.config['results']['promotions'] = self.config['promotions']

    def teardown(self):
        with open(self.config['stage-info-path'], "r") as stage_info:
            results = yaml.safe_load(stage_info)

        # We don't cleanup fixtures from the db
        # remove the db file is cleaner and quicker
        if (self.config['components'] == "all"
           or "inject-dlrn-fixtures" in self.config['components']):
            os.unlink(self.config['db_filepath'])

        if (self.config['components'] == "all"
           or "registries" in self.config['components']):
            self.teardown_registries(results['registries'])

        if (self.config['components'] == "all"
           or "container-images" in self.config['components']):
            os.unlink(self.config['containers']['pattern_file_path'])

        if (self.config['components'] == "all"
           or "overcloud-images" in self.config['components']):
            directory = self.config['overcloud_images']['base_dir']
            try:
                self.log.debug("removing %s", directory)
                shutil.rmtree(directory)
            except OSError:
                self.log.error("Error removing directory")
                raise

        # We don't need to teardown all the containes created. The containers
        # are deleted immediately after pushing them to the source registry

        os.unlink(self.config['stage-info-path'])

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


def load_config(overrides, db_filepath=None):
    """
    This loads the yaml configuration file containing information on paths
    and distributions to stage
    Also adds some static informations
    """

    base_path = os.path.dirname(os.path.abspath(__file__))

    config_file = os.path.join(base_path, "stage-config.yaml")
    with open(config_file) as cf:
        config = yaml.safe_load(cf)

    # fixtures are the basis for all the environment
    # not just for db injection, they contain the commit info
    # on which the entire promotion is based.
    config['db_fixtures'] = os.path.join(
        base_path, "fixtures", "scenario-1.yaml")

    config['results'] = {}

    config.update(overrides)

    if (config['components'] == "all"
       or "inject-dlrn-fixtures" in config['components']):
        if db_filepath is None:
            db_filepath = os.path.join(os.environ['HOME'], "commits.sqlite")
        config['db_filepath'] = db_filepath

    return config


def main():

    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger("promoter-staging")
    log.setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('action', choices=['setup', 'teardown'])
    components = [
        "all(default)",
        "inject-dlrn-fixtures",
        "overcloud-images",
        "container-images",
        "registries",
    ]
    parser.add_argument('--components', default="all",
                        help="Select components to create,".join(components))
    parser.add_argument('--dry-run', action='store_true', default=False,
                        help="Don't do anything, still create stage-info")
    parser.add_argument('--promoter-user', default=os.environ.get("USER",
                                                                  "centos"),
                        help="The promoter user")
    args = parser.parse_args()

    # Cli argument overrides over config
    overrides = {
        "components": args.components,
        "stage-info-path": "/tmp/stage-info.yaml",
        "dry-run": args.dry_run,
        "promoter_user": args.promoter_user
    }
    config = load_config(overrides)

    staged_env = StagedEnvironment(config)
    if args.action == 'setup':
        staged_env.setup()
    elif args.action == 'teardown':
        staged_env.teardown()


if __name__ == "__main__":
    main()
