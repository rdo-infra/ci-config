"""
This file contains classes and function to build a configuration object that
can be passed to all the functions in the workfloww
"""

import common
import copy
import logging
import os
import pprint
import yaml

from common import setup_logging, get_root_paths
from jinja2 import Template


class ConfigError(Exception):
    pass


class PromoterConfig(object):

    def __init__(self):
        self.locked = False
        self.default_settings = {}
        self.file_settings = {}
        self.cli_setting = {}
        self.set_handlers = {
            for target_name, info in config['promotions'].items():
                info['criteria'] = set(info['criteria'])
        }
        self.get_handlers = {
            'dlrnauth_password': os.environ.get('DLRNAPI_PASSWORD', None),
            'distro_name': self.distro_name.lower()
            'allowed_clients': self.allowed_clients.split(',')
        }

    def __setattr_(self, key, value):
        if self.locked:
            raise AttributeError("Config is read only")
        else:
            self.__dict__[key] = value

    def precedence(self):
        try:
            return self.cli_settings[name]
        except KeyError:
            pass
        try:
            return self.file_settings[name]
        except KeyError:
            pass
        try:
            return self.default_settings[name]
        except KeyError:
            pass

        raise AttributeError

    def __getattribute__(self, name):
        if name in
        attribute = object.__getattribute__(self, name)
        if isinstance(attribute, str):
            pass
        elif callable(attribute):
            return attribute()

        template_pass = Template(getattr(object, templated_value))
        while True:
            pass

        return output.encode("utf-8")

        value = template.render(self.__dict__)
        return value



class PromoterConfigGenerator(object):
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

        self.git_root, self.script_root = get_root_paths(self.log)
        self.log.debug("Git root %s", self.git_root)

    def __call__(self, config_path, filters="all", validate="all"):
        self.log.debug("Config file passed: %s", config_path)
        if config_path is None:
            raise ConfigError("Empty config file")
        # The path is either absolute ot it's relative to the code root
        if not os.path.isabs(config_path):
            config_path = os.path.join(self.script_root, "config",
                                       config_path)
        try:
            os.stat(config_path)
        except OSError:
            self.log.error("Configuration file not found")
            raise

        config = self.load_config(config_path)

        config = self.launch_filters(config, filters)
        if not self.validate(config, checks=validate):
            self.log.error("Error in configuration file %s", config_path)
            raise ConfigError

        configobj = type("ConfigObj", (), config)

        return configobj

    def load_config(self, config_path):
        """
        Basic checks on the config, the loads i into a dictionary
        :param config_path: the path to the configuration file to load
        :return:  A dict with the configuration
        """

        self.log.debug("Using config file %s", config_path)
        _config = self.load_from_yaml(config_path)
        config = copy.deepcopy(self.defaults)
        for key, value in config.items():
            try:
                config[key] = _config[key]
            except KeyError:
                self.log.warning("Config missing key %s. Using default value "
                                 "%s", key, value)

        return config

    def load_from_yaml(self, config_path):
        """
        Loads configuration from a yaml file.
        :param config_path: the path to the config file
        :return: a dict with the configuration
        """

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
                with open(config['log_file'], "w"):
                    pass
            except (FileNotFoundError, PermissionError):
                conf_ok = False
            try:
                getattr(logging, config['log_level'])
            except AttributeError:
                self.log.error("unrecognized log level: %s",
                               config['log_level'])
                conf_ok = False
        if "promotions" in checks:
            if 'promotions' not in config:
                self.log.error("Missing promotions section")
                conf_ok = False
            if not config['promotions']:
                self.log.error("Promotions section is empty")
                conf_ok = False
            for target_name, info in config['promotions'].items():
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
            if config.get('dlrnauth_password', None) is None:
                self.log.error("No dlrnapi password found in env")
                conf_ok = False

        return conf_ok

    def launch_filters(self, config, filters="all"):

        if not filters:
            return config

        if filters == "all":
            filters = ['overrides', 'expand']
        if 'overrides' in filters:
            config = self.handle_overrides(self._config, overrides)
        if 'expand' in filters:
            config = self.expand_config(config)
        # Add experimental configuration if activated
        if 'experimental' in filters \
           and config.get('experimental', False):
            config = self.experimental_config(config)

        return config

    def handle_overrides(self, config, overrides):
        """
        replaces selected config variables with values coming from command
        line arguments.
        :param config: The starting _config dict
        :param overrides: A namespace object with config overrides.
        :return: the overridden _config dict
        """

        main_overrides = ['log_file',
                          'promotions',
                          'api_url',
                          'username',
                          'repo_url',
                          'experimental',
                          'log_level',
                          'containers_list_base_url',
                          'allowed_clients']
        for override in main_overrides:
            try:
                attr = getattr(overrides, override)
                config[override] = attr
            except AttributeError:
                self.log.debug("Main config key %s not overridden", override)

        return config

    def get_dlrn_api_url(self, config):
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

    def expand_config(self, config):
        # Mangling, diverging and derivatives
        if 'api_url' not in config:
            config['api_url'] = self.get_dlrn_api_url(config)



        return config

    def experimental_config(self, config):
        """
        Loads additional configuration for experimental features
        :param config:
        :return:
        """
        # Experimental configuration for qcow promotion via promoter code
        # FIXME: This is policy and it shouldn't be here. Promotion
        #  configuration file should pass their server preference as variable
        default_qcow_server = 'staging'
        experimental_path = os.path.join(self.git_root, "ci-scripts",
                                         "dlrnapi_promoter",
                                         "promoter_defaults_experimental.yaml")
        with open(experimental_path, 'r') as \
                defaults:
            experimental_config = yaml.safe_load(defaults)

        if 'rhel' in self.distro_name or 'redhat' in self.distro_name:
            default_qcow_server = 'private'

        self.qcow_server = experimental_config['overcloud_images'][
            'qcow_servers'][default_qcow_server]

        return config
