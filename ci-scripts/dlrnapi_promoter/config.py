"""
This file contains classes and function to build a configuration object that
can be passed to all the functions in the workfloww
"""

import common
import logging
import os
import pprint
import yaml

from common import setup_logging, get_root_paths
from jinja2 import Template
from collections import OrderedDict


class ConfigError(Exception):
    pass


class PromoterConfig(object):

    log = logging.getLogger("promoter")

    def __init__(self, default_settings=None, file_settings=None,
                 cli_settings=None, experimental_settings=None):
        if cli_settings is None:
            cli_settings = {}
        if file_settings is None:
            file_settings = {}
        if default_settings is None:
            default_settings = {}
        if experimental_settings is None:
            experimental_settings = {}
        self.settings = OrderedDict()
        self.settings["cli"] = cli_settings
        self.settings['file'] = file_settings
        self.settings['default'] = default_settings
        self.settings['experimental'] = experimental_settings

    def __getitem__(self, attribute_name):
        return self.__getattr__(attribute_name)

    def __getattr__(self, attribute_name):
        try:
            attribute = self.__dict__[attribute_name]
            self.log.debug("Getting attribute %s directly from instance",
                           attribute_name)
            return attribute
        except KeyError:
            pass

        defined = False
        for source in self.settings.keys():
            try:
                attribute = self.settings[source][attribute_name]
                self.log.debug("Getting attribute %s from %s settings",
                               attribute_name, source)
                defined = True
                break
            except KeyError:
                pass

        handler_name = "get_handler_{}".format(attribute_name)
        handler = None
        try:
            handler = self.__getattribute__(handler_name)
        except AttributeError:
            pass
        filter_name = "get_filter_{}".format(attribute_name)
        filter = None
        try:
            filter = self.__getattribute__(filter_name)
        except AttributeError:
            pass

        if handler and not defined:
            self.log.debug("Running handler for attribute %s",
                           attribute_name)
            attribute = handler()
            defined = True

        if filter and defined:
            self.log.debug("Running filter for attribute %s",
                           attribute_name)
            attribute = filter(attribute)

        if not defined:
            raise AttributeError

        if isinstance(attribute, str):
            template = Template(attribute)
            value = template.render(self.__dict__)
            return value
        elif callable(attribute):
            return attribute()
        else:
            return attribute

    # Handlers

    def get_handler_dlrnauth_password(self):
        return os.environ.get('DLRNAPI_PASSWORD', None)

    def get_handler_qcow_server(self):
        return self['overcloud_images']['qcow_servers'][
            self.default_qcow_server]

    def get_handler_api_url(self):
        """
        API url is the wild west of exceptions, when it's not specified in
        config files, we need an entire function to try to understand what we
        can use
        :param config: The existing configuration
        :return: the first API url that responds.
        """
        # Try local staged api first
        api_host = "localhost"
        api_port = 58080
        api_url = None
        if common.check_port(api_host, api_port):
            api_url = "http://{}:{}".format(api_host, api_port)
        else:
            distro_api_endpoint = config['distro_name']
            if config['distro_version'] == '8':
                distro_api_endpoint += config['distro_version']
            release_api_endpoint = config['release']
            if config['release'] == "master":
                release_api_endpoint = "master-uc"
            api_endpoint = "api-{}-{}".format(distro_api_endpoint,
                                              release_api_endpoint)
            api_host = self.defaults['dlrn_api_host']
            api_port = 443
            if common.check_port(api_host, api_port, 5):
                api_url = "https://{}/{}".format(api_host, api_endpoint)

        if api_url is None:
            self.log.error("No valid API url found")
        else:
            self.log.debug("Assigning api_url %s", api_url)
        return api_url

    # filters

    def get_filter_allowed_clients(self, allowed_clients):
        return allowed_clients.split(',')

    def get_filter_distro_name(self, distro_name):
        return distro_name.lower()

    def set_filter_promotions(self, promotions):
        for target_name, info in promotions.items():
            if not isinstance(info['criteria'], set):
                info['criteria'] = set(info['criteria'])


class PromoterConfigFactory(object):
    """
    This class builds a singleton object to be passed to all the other
    functions in the workflow.
    The base class should be only used for testing as it just performs the
    basic loading.
    """

    defaults = {
        'release': 'master',
        'distro_name': 'centos',
        'distro_version': '7',
        'dlrnauth_username': 'ciuser',
        'promotions': {},
        'dry_run': "false",
        'manifest_push': "false",
        'target_registries_push': "true",
        'latest_hashes_count': '10',
        'allowed_clients': 'registries_client,qcow_client,dlrn_client',
        'log_level': "INFO",
        'log_file': None,
        "dlrn_api_host": "trunk.rdoproject.org",
        "containers_list_base_url": ("https://opendev.org/openstack/"
                                     "tripleo-common/raw/commit/"),
        "containers_list_path": "container-images/overcloud_containers.yaml.j2",
        "repo_url": "https://{{ dlrn_api_host }}/{{ distro }}-{{ release }}",
        'log_file': "~/promoter_logs/{{ distro }}_{{ distro }}.log",
        "distro": "{{ distro_name }}{{ distro_release }}"
    }

    log = logging.getLogger("promoter")

    def __init__(self, filters="all", validate="all"):
        """
        Initialize the config object loading from ini file
        :param config_path: the path to the configuration file to load
        :param validate: A comma separated list of checks for the config
        file
        """
        # Initial log setup
        setup_logging("promoter", logging.DEBUG)
        self.git_root = None
        self.script_root = None
        self.git_root, self.script_root = get_root_paths(self.log)
        self.log.debug("Git root %s", self.git_root)
        self.log.debug("Script root %s", self.git_root)

    def __call__(self, config_path, cli_settings=None, validate="all"):
        file_settings = self.load_file_settings(config_path)
        experimental_path = os.path.join(self.script_root,
                                         "promoter_defaults_experimental.yaml")
        experimental_settings = self.load_file_settings(experimental_path)

        config = PromoterConfig(default_settings=self.defaults,
                                file_settings=file_settings,
                                cli_settings=cli_settings,
                                experimental_settings=experimental_settings)

        if not self.validate(config, checks=validate):
            self.log.error("Error in configuration file %s", config_path)
            raise ConfigError

        return config

    def load_file_settings(self, config_path):
        """
        Loads configuration from a yaml file.
        :param config_path: the path to the config file
        :return: a dict with the configuration
        """

        self.log.debug("Config file passed: %s", config_path)
        if config_path is None:
            self.log.error("Config file passed can't be None")
            raise ConfigError
        # The path is either absolute ot it's relative to the code root
        if not os.path.isabs(config_path):
            config_path = os.path.join(self.script_root, "config",
                                       config_path)
        try:
            os.stat(config_path)
        except OSError:
            self.log.error("Configuration file not found")
            raise

        self.log.debug("Using config file %s", config_path)
        with open(config_path) as config_file:
            try:
                config = yaml.safe_load(config_file)
            except yaml.YAMLError as exc:
                self.log.error("Unable to load config file %s", config_path)
                self.log.exception(exc)
                raise ConfigError
        if not isinstance(config, dict):
            self.log.error("Config file %s does not contain valid data",
                           config_path)
            raise ConfigError

        return config

    def validate(self, config, checks="all"):
        """
        :param config:
        :param checks:
        :return:
        """
        if not checks:
            return True

        conf_ok = True
        if checks == "all":
            checks = ["logs", "password", "promotions"]
        if 'logs' in checks:
            try:
                with open(config.log_file, "w"):
                    pass
            except (FileNotFoundError, PermissionError):
                conf_ok = False
            try:
                getattr(logging, config.log_level)
            except AttributeError:
                self.log.error("unrecognized log level: %s",
                               config['log_level'])
                conf_ok = False

        if "promotions" in checks:
            promotions = getattr(config, 'promotions', None)

            if promotions is None:
                self.log.error("Missing promotions section")
                conf_ok = False
            elif not promotions:
                self.log.error("Promotions section is empty")
                conf_ok = False
            else:
                for target_name, info in promotions.items():
                    if 'criteria' not in info:
                        self.log.error("Missing criteria for target %s",
                                       target_name)
                        conf_ok = False
                    if 'criteria' in info and not info['criteria']:
                        self.log.error("Empty criteria for target %s",
                                       target_name)
                        conf_ok = False
                    if 'candidate_label' not in info:
                        self.log.error("Missing candidate label for target %s",
                                       target_name)
                        conf_ok = False

        if "password" in checks:
            try:
                if config.dlrnauth_password is None:
                   raise AttributeError
            except AttributeError:
                self.log.error("No dlrnapi password found in env")
                conf_ok = False

        return conf_ok

