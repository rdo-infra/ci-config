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
import logging
import os
import pprint
import shutil
import yaml

from string import Template
from stage_dlrn import DlrnStagingServer
from stage_qcows import QcowStagingServer
from stage_registries import StagingRegistries
from stage_containers import StagingContainers
from stage_config import StageConfig


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

        self.scenes_controllers = {
            'dlrn': DlrnStagingServer(self.config),
            "registries": StagingRegistries,
            "overcloud_images": QcowStagingServer,
            "containers": StagingContainers,
        }

        self.scenes = self.config.main['scenes']

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
        stage_info['distro_name'] = self.distro_name
        stage_info['distro_version'] = self.distro_version
        stage_info['release'] = self.release
        stage_info['logfile'] = logfile
        stage_info['scenes'] = self.scenes
        stage_info['promoter_user'] = self.promoter_user
        pipeline_type = "single"
        if self.config.main['components_mode']:
            pipeline_type = "integration"
        stage_info['pipeline_type'] = pipeline_type

        return stage_info

    def setup(self):
        """
        Orchestrates the setting up of the environment
        """
        self.log.info("Creating stage root dir in %s" % self.stage_root)
        if not self.dry_run:
            try:
                os.makedirs(self.stage_root)
            except OSError:
                self.log.info("Stage root dir exists, not creating")

        # If the stages is in in component mode, it's mandatory dlrn is run
        if 'dlrn' in self.scenes or self.config.main['components_mode']:
            self.scenes_controllers['dlrn'].setup()

        # We need dlrn stage info even if it's not fully run as they are
        # reference for every other operation
        stage_info_content = {
            'dlrn': self.scenes_controllers['dlrn'].stage_info
        }

        if 'registries' in self.scenes or 'containers' in self.scenes:
            controller = self.scenes_controllers['registries'](self.config)
            stage_info_content['registries'] = controller.setup()
        if 'containers' in self.scenes:
            controller = self.scenes_controllers['containers'](self.config)
            stage_info_content['containers'] = controller.setup()
        if 'overcloud_images' in self.scenes:
            controller = \
                self.scenes_controllers['overcloud_images'](self.config)
            stage_info_content['overcloud_images'] = controller.setup()

        stage_info_content['main'] = self.stage_info
        stage_info_yaml = yaml.safe_dump(stage_info_content)
        with open(self.stage_info_path, "w") as stage_info_file:
            stage_info_file.write(stage_info_yaml)

    def teardown(self):
        with open(self.stage_info_path, "r") as stage_info_file:
            stage_info = yaml.safe_load(stage_info_file)

        self.scenes = stage_info['main']['scenes']

        if 'dlrn' in self.scenes or self.config.main['components_mode']:
            self.scenes_controllers['dlrn'].teardown(stage_info)

        # We need dlrn stage info even if it's not fully run as they are
        # reference for every other operation
        if 'registries' in self.scenes:
            controller = self.scenes_controllers['registries'](self.config)
            controller.teardown(stage_info)
        if 'containers' in self.scenes:
            controller = self.scenes_controllers['containers'](self.config)
            controller.teardown(stage_info)
        if 'overcloud_images' in self.scenes:
            controller = \
                self.scenes_controllers['overcloud_images'](self.config)
            controller.teardown(stage_info)

        self.log.info("Removing stage root dir in %s" % self.stage_root)
        if not self.dry_run:
            try:
                shutil.rmtree(self.stage_root)
            except OSError:
                self.log.info("Stage root dir doesn't exists, not removing")

        os.unlink(self.stage_info_path)


def parse_args(cmd_line=None):
    defaults = StageConfig.defaults
    parser = argparse.ArgumentParser(description='Staging promoter')
    parser.add_argument('action', choices=['setup', 'teardown'])
    default_scenes = ','.join(defaults.scenes)
    parser.add_argument('--scenes',
                        default=default_scenes,
                        help=("Select scenes to create in the environment "
                              "scenes available {}"
                              "".format(default_scenes))
                        ),
    parser.add_argument('--dry-run', action='store_true', default=False,
                        help="Don't do anything, still create stage-info")
    parser.add_argument('--promoter-user',
                        default=defaults.promoter_user,
                        help="The promoter user")
    parser.add_argument('--stage-config-file',
                        default=defaults.stage_config_file,
                        help=("Config file for stage generation"
                              " (relative to config dir)"))
    parser.add_argument('--stage-info-file',
                        default=defaults.stage_info_file,
                        help=("Config file for stage results"))
    parser.add_argument('--db-data-file',
                        default=defaults.db_data_file,
                        help=("Data file to inject to dlrn server"
                              " (relative to config dir)"))
    if cmd_line is not None:
        args = parser.parse_args(cmd_line.split())
    else:
        args = parser.parse_args()

    if hasattr(args, 'scenes'):
        args.scenes = args.scenes.split(',')

    return args


def main(cmd_line=None):

    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger("promoter-staging")
    log.setLevel(logging.DEBUG)

    args = parse_args(cmd_line=cmd_line)

    config = StageConfig(source=args.stage_config_file, overrides=args)

    staged_env = StagedEnvironment(config)
    if args.action == 'setup':
        staged_env.setup()
    elif args.action == 'teardown':
        staged_env.teardown()
    else:
        log.error("No action specified")

    if cmd_line is not None:
        return config


if __name__ == "__main__":
    main()
