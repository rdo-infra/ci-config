import logging
import os
import shutil

import yaml

from stage_containers import StagingContainers
from stage_dlrn import DlrnStagingServer
from stage_qcows import QcowStagingServer
from stage_registries import StagingRegistries

try:
    # Python 3 import
    import configparser as ini_parser
except ImportError:
    # Python 2 import
    import ConfigParser as ini_parser


class StageOrchestrator(object):
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
        pipeline_type = "single"
        if self.config.main['components_mode']:
            pipeline_type = "integration"

        stage_info = {
            'distro_name': self.distro_name,
            'distro_version': self.distro_version,
            'release': self.release, 'log_file': self.log_file,
            'scenes': self.scenes,
            'promoter_user': self.promoter_user,
            'pipeline_type': pipeline_type,
            'promoter_config_file': self.config.main['promoter_config_file']
        }

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
