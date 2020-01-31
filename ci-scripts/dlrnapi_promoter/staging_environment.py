"""
This script emulates the state of the environment around promoter as it would be
just before starting a promotion process.

The promotion interacts with:
    - dlrn_api (staged locally as standalone service)
    - docker registries (staged locally with registries on different ports)
    - images server (staged locally as normal sftp via ssh)

It can setup different components independently, the list of components it
handles it's currently defined by the "scenes" variable

This provisioner should produce

- A database usable by dlrnapi that contains hashes, users, votes from jobs
- A hierarchy for overcloud images, so image promotion script can
  sftp to localhost and change the links accordingly
- A containers definition file, oused by container-push
  playbook as a list of containers to promote.
- a yaml file containing reusable information on what this script produced for
  the components called
- A set of images pushed to source registry, so the promoter has the container
  to pull and  push during the promotion run
- A file with all information on what was produced by an executions
"""
import argparse
import logging
import os
import pprint
import shutil
import yaml

from stage_dlrn import DlrnStagingServer
from stage_qcows import QcowStagingServer
from stage_registries import StagingRegistries
from stage_containers import StagingContainers
from stage_config import StageConfig


class StagedEnvironment(object):
    """
    This class drives the top level staging parts:
    - maps the controllers for the various scenes
    - calls the setup method for the controllers in the selected scenes
    - gather stage_info information and dumps the into a file
    - calls the teardown methods of all scene controllers at the end
    """

    log = logging.getLogger("promoter-staging")

    def __init__(self, config):
        """
        like many inits around the code, this loads the config and create
        shortcuts for the used configuration parameters
        This init also maps the scenes to their controllers
        :param config: The global stage config
        """
        self.config = config
        self.dlrn_server = DlrnStagingServer(config)
        self.log_file = self.config.main['log_file']
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
        """
        Property that returns the dict with info on the main options for the
        stage
        :return: A dict with useful info
        """
        stage_info = {}
        stage_info['distro_name'] = self.distro_name
        stage_info['distro_version'] = self.distro_version
        stage_info['release'] = self.release
        stage_info['log_file'] = self.log_file
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
        Creates the stage root dir and calls the various scenes setup
        Then create the stag info file
        :return: None
        """
        self.log.info("Creating stage root dir in %s" % self.stage_root)
        if not self.dry_run:
            try:
                os.makedirs(self.stage_root)
            except OSError:
                self.log.info("Stage root dir exists, not creating")

        # If the stage is in in component mode, it's mandatory dlrn is run
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

        # Create the stage info file with all the information
        # Gathered from all the stage info returned by the controller setup
        # methods
        stage_info_content['main'] = self.stage_info
        stage_info_yaml = yaml.safe_dump(stage_info_content)
        with open(self.stage_info_path, "w") as stage_info_file:
            stage_info_file.write(stage_info_yaml)

    def teardown(self):
        """
        This orchestrates the stage cleanup calling the various teardown methods
        from the scene controllers.
        :return:
        """
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

        # finally remove the stage_info file as the stage is no more
        os.unlink(self.stage_info_path)


def parse_args(cmd_line=None):
    """
    parses command line arguments
    :param cmd_line: an optional str paramter to simlate a command line.
    Useful for testing this function
    :return: The argparse args namespace object with cli arguments
    """

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
    parser.add_argument('--promoter-config-file',
                        default=defaults.promoter_config_file,
                        help=("Promoter fileConfig file for promoter"
                              " on whic to base the stage"
                              " (relative to config dir)"))

    # Parse from the function parameter if present
    if cmd_line is not None:
        args = parser.parse_args(cmd_line.split())
    else:
        args = parser.parse_args()

    if hasattr(args, 'scenes'):
        args.scenes = args.scenes.split(',')

    return args


def main(cmd_line=None):
    """
    The main sets up logging and instantiates the Config object and the staging
    environment object.
    The calls the proper action based on the mandatory action command line
    argument.
    :param cmd_line: an optional parameter to pass to the argument parser
    function
    :return: the configuration produced if a cmd_line has been passed. None
    otherwise. Useful for testing of the main function
    """

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
