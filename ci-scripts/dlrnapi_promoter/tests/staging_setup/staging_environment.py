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
import copy
import logging
import os
import pprint
import shutil
import tempfile
import yaml

from string import Template
from dlrn_server import DlrnStagingServer


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
        self.dlrn_server = DlrnStagingServer(config)
        self.logfile_template = self.config.main['logfile_template']
        self.distro_name = self.config.main['distro_name']
        self.distro_version = self.config.main['distro_version']
        self.promoter_user = self.config.main['promoter_user']
        self.release = self.config.main['release']
        self.stage_root = self.config.main['stage_root']
        self.dry_run = self.config.main['dry_run']
        self.stage_info_path = self.config.main['stage_info_path']

        self.scenes = self.config.main['scenes']

        self.scenes_controllers = {
            "dlrn": DlrnStagingServer(self.config),
            # "registries": StagingRegistries(self.config),
            # "overcloud-images": QcowStagingServer(self.config),
            # "container-images": StagingContainers(self.config)
        }

        self.log.info("Creating stage root dir in %s" % self.stage_root)
        if not self.dry_run:
            try:
                os.makedirs(self.stage_root)
            except OSError:
                self.log.info("Stage root dir exists, not creating")

    @property
    def stage_info(self):
        stage_info = {}
        template = Template(self.logfile_template)
        logfile = template.substitute({
            'distro_name': self.distro_name,
            'distro_version': self.distro_version,
            'promoter_user': self.promoter_user,
            'release': self.release,
        })
        stage_info['logfile'] = logfile
        stage_info['scenes'] = self.scenes

        return stage_info

    def setup(self):
        """
        Orchestrates the setting up of the environment
        """
        stage_info_content = {}
        stage_info_content['main'] = self.stage_info
        for scene in self.scenes:
            try:
                scene_controller = self.scenes_controllers[scene]
            except KeyError:
                raise Exception("No controller found for scene %s" % scene)
            stage_info_content[scene] = scene_controller.setup()

        stage_info_yaml = yaml.dump(stage_info_content)
        with open(self.stage_info_path, "w") as stage_info_file:
            stage_info_file.write(stage_info_yaml)

    def teardown(self):
        with open(self.stage_info_path, "r") as stage_info_file:
            stage_info = yaml.safe_load(stage_info_file)

        for scene in stage_info['main']['scenes']:
            scene_controller = self.scenes_controllers[scene]
            scene_controller.teardown()

        os.unlink(self.stage_info_path)


class StageConfig(object):

    log = logging.getLogger("promoter-staging")

    def __init__(self, source=None, overrides=None):
        """
        This loads the yaml configuration file containing information on paths
        and distributions to stage
        Also adds some static informations
        """

        # config Sections
        self.dlrn = None
        self.registries = None
        self.containers = None
        self.main = None
        self.overcloud_images = None

        self.code_root = os.path.dirname(os.path.abspath(__file__))
        # load from source
        _config = {}
        if source is None:
            # ith empty source we default with default config file
            source = "stage-config.yaml"
        if type(source) == str:
            # A str source is a file name in yaml to load
            config_path = os.path.join(self.code_root, source)
            with open(config_path) as cf:
                _config = yaml.safe_load(cf)
        elif type(source) == dict:
            _config = source
        else:
            raise Exception("No config source specified")

        # Additional filters to configuration
        _config = self.handle_overrides(_config, overrides)
        _config = self.convert_paths(_config)
        _config = self.augment_config(_config)

        # Fill sections
        for section_name, section_data in _config.items():
            setattr(self, section_name, section_data)

    def augment_config(self, _config):
        # Extract and manipulate useful data from config and db data
        distro ="{}{}".format(_config['main']['distro_name'],
                              _config['main']['distro_version'])
        _config['main']['distro'] = distro

        # fixtures are the basis for all the environment
        # not just for db injection, they contain the commit info
        # on which the entire promotion is based.
        db_data_path = _config['dlrn']['server']['db_fixtures']
        with open(db_data_path) as db_data_file:
            _config['dlrn']['server']['db_data'] = yaml.safe_load(db_data_file)

        if _config['main']['pipeline_type'] == "single":
            commits = []
            promotion_map = {}
            promotions = copy.deepcopy(_config['dlrn']['server']['db_data'][
                                       'promotions'])
            for promotion in promotions:
                promotion_map[promotion['commit_id']] = \
                    promotion['promotion_name']

            for db_commit in _config['dlrn']['server']['db_data']['commits']:
                commit = copy.deepcopy(db_commit)
                # Find name for commit in promotions if exists
                try:
                    commit['name'] = promotion_map[db_commit['id']]
                except KeyError:
                    pass
                commits.append(commit)

            # First commit is currently promoted
            currently_promoted = commits[0]
            # Second commit is previously promoted
            previously_promoted = commits[1]
            # Last commit is the promotion candidate
            promotion_candidate = commits[-1]
            _config['dlrn']['commits'] = commits
            _config['dlrn']['promotions'] = {
                'currently_promoted': currently_promoted,
                'previously_promoted': previously_promoted,
                'promotion_candidate': promotion_candidate,
            }
            _config['dlrn']['rev_promotions'] = {
                currently_promoted['id']: 'currently_promoted',
                previously_promoted['id']:'previously_promoted',
                promotion_candidate['id']: 'promotion_candidate',
            }
        elif _config['main']['pipeline_type'] == "component":
            commits = []
            components = _config['dlrn']['components']
            n_components = len(components)
            # This dictionary specifies the slices to use on the db_commits
            # to divide the set of commits into three sets corresponding
            # to three promotions
            promotion_map = {
                'currently_promoted': {
                    'name': 'tripleo-ci-staging-promoted',
                    'slice': slice(0, n_components),
                },
                'previously_promoted': {
                    'name': 'previous-tripleo-ci-staging-promoted',
                    'slice': slice(n_components, n_components*2),
                },
                'promotion_candidate': {
                    'name': 'tripleo-ci-staging',
                    'slice': slice(n_components * 2, n_components * 3),
                }
            }
            db_commits = _config['dlrn']['server']['db_data']['commits']
            for promotion_alias, values in promotion_map.items():
                for index, db_commit in enumerate(db_commits[values['slice']]):
                    commit = copy.deepcopy(db_commit)
                    commit['name'] = values['name']
                    commit['component'] = components[index]
                    commits.append(commit)
            _config['dlrn']['commits'] = commits



        return _config

    def handle_overrides(self, _config, overrides):
        # Handle overrides
        main_overrides = ('scenes', 'dry_run', 'promoter_user', 'pipeline_type')
        for override in main_overrides:
            try:
                attr = overrides[override]
                _config['main'][override] = attr
            except KeyError:
                self.log.debug("Main config key %s not overridden" % override)
            except TypeError:
                # overrides exists but it's None
                pass

        try:
            _config['dlrn']['server']['db_fixtures'] = overrides.fixture_file
        except AttributeError:
            pass

        return _config

    def convert_paths(self, _config):
        # convert relative paths to absolute
        stage_root = _config['main']['stage_root']

        dlrn_root = os.path.join(stage_root, _config['dlrn']['server']['root'])
        _config['dlrn']['server']['root'] = dlrn_root

        repo_root = os.path.join(dlrn_root,
                                 _config['dlrn']['server']['repo_root'])
        _config['dlrn']['server']['repo_root'] = repo_root

        db_fixtures = os.path.join(self.code_root, "fixtures",
                                   _config['dlrn']['server']['db_fixtures'])
        _config['dlrn']['server']['db_fixtures'] = db_fixtures

        db_file = os.path.join(dlrn_root,
                                   _config['dlrn']['server']['db_file'])
        _config['dlrn']['server']['db_file'] = db_file

        return _config


def parse_args():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('action', choices=['setup', 'teardown'])
    scenes = (
        "dlrn",
        "overcloud-images",
        "container-images",
        "registries",
    )
    parser.add_argument('--scenes', default="all",
                        help="Select scenes to create in the environment",
                        choices=scenes)
    parser.add_argument('--dry-run', action='store_true', default=False,
                        help="Don't do anything, still create stage-info")
    parser.add_argument('--promoter-user', default=os.environ.get("USER",
                                                                  "centos"),
                        help="The promoter user")
    parser.add_argument('--stage-config-file', default="stage-config.yaml",
                        help=("Config file for stage generation"
                              " (relative to config dir)"))
    parser.add_argument('--fixture-file', default="scenario-1.yaml",
                        help=("Fixture to inject to dlrn server"
                              " (relative to config dir)"))
    parser.add_argument('--pipeline-type', default="single",
                        help=("Define the pipeline type"),
                        choices=("single", "component"))
    args = parser.parse_args()

    if hasattr(args, 'scenes'):
        args.scenes = args.scenes.split(',')

    return args


def main():

    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger("promoter-staging")
    log.setLevel(logging.DEBUG)

    args = parse_args()

    config = StagingConfig(source=args.stage_config_file, overrides=args)

    staged_env = StagedEnvironment(config)
    if args.action == 'setup':
        staged_env.setup()
    elif args.action == 'teardown':
        staged_env.teardown()
    else:
        self.log.error("No action specified")


if __name__ == "__main__":
    main()
