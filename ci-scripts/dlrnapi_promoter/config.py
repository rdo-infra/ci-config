"""
This file contains classes and function to build a configuration object that
can be passed to all the functions in the workfloww
"""

try:
    # Python 3 import
    import configparser as ini_parser
except ImportError:
    # Python 2 import
    import ConfigParser as ini_parser

import common
import copy
import logging
import os
import pprint
import yaml

from common import str2bool, setup_logging, LoggingError, \
    get_root_paths

# Try to import stageconfig for defaults
try:
    from stage_config import StageConfig
except ImportError:
    pass


class ConfigError(Exception):
    pass


def load_defaults(config_root_path):
    defaults_path = os.path.join(config_root_path, "defaults.yaml")
    with open(defaults_path) as defaults_file:
        defaults = yaml.safe_load(defaults_file)

    return defaults


class PromoterConfigBase(object):
    """
    This class builds a singleton object to be passed to all the other
    functions in the workflow.
    The base class should be only used for testing as it just performs the
    basic loading.
    """

<<<<<<< HEAD
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
        "containers_list_path": "container-images/overcloud_containers.yaml.j2"
    }
||||||| parent of 6188269... [WIP] Promoter: add support multiple configuration environments
    defaults = {
        'release': 'master',
        'distro_name': 'centos',
        'distro_version': '7',
        'dlrnauth_username': 'ciuser',
        'promotion_steps_map': {},
        'promotion_criteria_map': {},
        'dry_run': "false",
        'manifest_push': "false",
        'target_registries_push': "true",
        'latest_hashes_count': '10',
        'allowed_clients': 'registries_client,qcow_client,dlrn_client',
        'log_level': "INFO",
        "dlrn_api_host": "trunk.rdoproject.org",
        "containers_list_base_url": ("https://opendev.org/openstack/"
                                     "tripleo-common/raw/commit/"),
        "containers_list_path": "container-images/overcloud_containers.yaml.j2"
    }
=======
>>>>>>> 6188269... [WIP] Promoter: add support multiple configuration environments
    log = logging.getLogger("promoter")

<<<<<<< HEAD
    def __init__(self, config_path, sanity_checks="all"):
||||||| parent of 6188269... [WIP] Promoter: add support multiple configuration environments
    def __init__(self, config_file):
=======
    def __init__(self, config_rel_path, config_root=None):
>>>>>>> 6188269... [WIP] Promoter: add support multiple configuration environments
        """
        Initialize the config object loading from ini file
        :param config_path: the path to the configuration file to load
        :param sanity_checks: A comma separated list of checks for the config
        file
        """
        # Initial log setup
        setup_logging("promoter", logging.DEBUG)

        self.git_root, self.script_root = get_root_paths(self.log)
<<<<<<< HEAD
        self.log.debug("Config file passed: %s", config_path)
||||||| parent of 6188269... [WIP] Promoter: add support multiple configuration environments
        self.log.debug("Config file passed: %s", config_file)
=======
        self.config_root = config_root
        if not self.config_root:
            self.config_root = os.path.join(self.script_root, "config")
        self.log.debug("Config file passed: %s", config_rel_path)
>>>>>>> 6188269... [WIP] Promoter: add support multiple configuration environments
        self.log.debug("Git root %s", self.git_root)
        self.defaults = load_defaults(self.config_root)

<<<<<<< HEAD
        if config_path is None:
||||||| parent of 6188269... [WIP] Promoter: add support multiple configuration environments
        if config_file is None:
=======
        if config_rel_path is None:
>>>>>>> 6188269... [WIP] Promoter: add support multiple configuration environments
            raise ConfigError("Empty config file")
        # The path is either absolute ot it's relative to the code root
<<<<<<< HEAD
        if not os.path.isabs(config_path):
            config_path = os.path.join(self.script_root, "config",
                                       config_path)
||||||| parent of 6188269... [WIP] Promoter: add support multiple configuration environments
        if not os.path.isabs(config_file):
            config_file = os.path.join(self.script_root, "config",
                                       config_file)
=======
        if not os.path.isabs(config_rel_path):
            self.log.error("Config file should always be relative config root")
        config_path = os.path.join(self.config_root, config_rel_path)
>>>>>>> 6188269... [WIP] Promoter: add support multiple configuration environments
        try:
            os.stat(config_path)
        except OSError:
            self.log.error("Configuration file not found")
            raise

<<<<<<< HEAD
        self._config = self.load_config(config_path)

        if not self.sanity_checks(self._config, checks=sanity_checks):
            self.log.error("Error in configuration file %s", config_path)
            raise ConfigError
||||||| parent of 6188269... [WIP] Promoter: add support multiple configuration environments
        self.log.debug("Using config file %s", config_file)
        self._file_config = self.load_from_ini(config_file)
        self._config = self.load_config(config_file, self._file_config)
=======
        self.log.debug("Using config file %s", config_path)
        self._file_config = self.load_from_ini(config_path)
        self._config = self.load_config(config_path, self._file_config)
>>>>>>> 6188269... [WIP] Promoter: add support multiple configuration environments

        # Load keys as config attributes
        for key, value in self._config.items():
            setattr(self, key, value)

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
        # This is done also in the child class, in expand config, but it's
        # really necessary to expand this even i the base class
        if config['log_file'] is not None:
            config['log_file'] = os.path.expanduser(config['log_file'])

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

    def sanity_checks(self, config, checks="all"):
        """
        There are several exceptions
        that can block the load
        - Missing criteria section for one of the specified candidates
        - Missing jobs in criteria section
        - Missing password
        """
        conf_ok = True
        if checks == "all":
            checks = ["logs", "password", "promotions"]
        if 'logs' in checks:
            try:
                setup_logging('promoter', config['log_level'],
                              config['log_file'])
            except LoggingError:
                conf_ok = False
            finally:
                common.close_logging('promoter')
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


class PromoterConfig(PromoterConfigBase):
    """
    This class expands and check the sanity of the config file. Only this
    class should be used by the promoter
    """

<<<<<<< HEAD
    def __init__(self, config_path, overrides=None, filters="all",
                 sanity_checks="all"):
||||||| parent of 6188269... [WIP] Promoter: add support multiple configuration environments
    def __init__(self, config_file, overrides=None, filters="all",
                 checks="all"):
=======
    def __init__(self, config_rel_path, overrides=None, filters="all",
                 checks="all"):
>>>>>>> 6188269... [WIP] Promoter: add support multiple configuration environments
        """
        Expands the parent init by adding config expansion, overrides
        handling and sanity checks
        :param config_path: the path to the configuration file to load
        :param overrides: An object with override for the configuration
        """
<<<<<<< HEAD
        super(PromoterConfig, self).__init__(config_path,
                                             sanity_checks=sanity_checks)
||||||| parent of 6188269... [WIP] Promoter: add support multiple configuration environments
        super(PromoterConfig, self).__init__(config_file)
=======
        super(PromoterConfig, self).__init__(config_rel_path)
>>>>>>> 6188269... [WIP] Promoter: add support multiple configuration environments

        config = {}
        if filters == "all":
            filters = ['overrides', 'expand', 'experimental']
        if 'overrides' in filters:
            config = self.handle_overrides(self._config, overrides)
        if 'expand' in filters:
            config = self.expand_config(config)
<<<<<<< HEAD
||||||| parent of 6188269... [WIP] Promoter: add support multiple configuration environments
        if not self.sanity_check(config, self._file_config, checks=checks):
            self.log.error("Error in configuration file {}"
                           "".format(config_file))
            raise ConfigError

=======
        if not self.sanity_check(config, self._file_config, checks=checks):
            self.log.error("Error in configuration file {}"
                           "".format(config_rel_path))
            raise ConfigError

>>>>>>> 6188269... [WIP] Promoter: add support multiple configuration environments
        # Add experimental configuration if activated
        if 'experimental' in filters \
           and str2bool(config.get('experimental', 'false')):
            config = self.experimental_config(config)

        # reLoad keys as config attributes
        for key, value in config.items():
            setattr(self, key, value)

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
        config['dlrnauth_password'] = os.environ.get('DLRNAPI_PASSWORD', None)
        config['distro_name'] = config['distro_name'].lower()
        config['distro'] = "{}{}".format(config['distro_name'],
                                         config['distro_version'])

        if 'repo_url' not in config:
            config['repo_url'] = ("https://{}/{}-{}"
                                  "".format(self.defaults['dlrn_api_host'],
                                            config['distro'],
                                            config['release']))

        if 'api_url' not in config:
            config['api_url'] = self.get_dlrn_api_url(config)

        if 'log_file' not in config:
            config['log_file'] = ("~/promoter_logs/{}_{}.log"
                                  "".format(config['distro'],
                                            config['release']))

        if config['log_file'] is not None:
            config['log_file'] = os.path.expanduser(config['log_file'])
        try:
            config['log_level'] = getattr(logging, config['log_level'])
        except AttributeError:
            self.log.error("unrecognized log level: %s, using default %s",
                           config['log_level'], self.defaults.log_level)
            config['log_level'] = self.defaults.log_level

        config['allowed_clients'] = \
            config.get('allowed_clients',
                       self.defaults['allowed_clients']).split(',')
        config['dry_run'] = \
            str2bool(config.get('dry_run', self.defaults['dry_run']))
        config['manifest_push'] = \
            str2bool(config.get('manifest_push',
                                self.defaults['manifest_push']))
        config['target_registries_push'] = \
            str2bool(config.get('target_registries_push',
                                self.defaults['target_registries_push']))

        # Promotion criteria do not have defaults
        for target_name, info in config['promotions'].items():
            info['criteria'] = set(info['criteria'])

        config['overcloud_images_server'] = \
            config['overcloud_images']['qcow_servers'][
                config['overcloud_images_server_name']]

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
