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

from common import str2bool, setup_logging, check_port, LoggingError, \
    get_root_paths

# Try to import stageconfig for defaults
try:
    from stage_config import StageConfig
except ImportError:
    pass


class ConfigError(Exception):
    pass


class PromoterConfigBase(object):
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
    log = logging.getLogger("promoter")

    def __init__(self, config_file):
        """
        Initialize the config object loading from ini file
        :param config_path: the path to the configuration file to load
        """
        # Initial log setup
        setup_logging("promoter", logging.DEBUG)

        self.git_root, self.script_root = get_root_paths(self.log)
        self.log.debug("Config file passed: %s", config_file)
        self.log.debug("Git root %s", self.git_root)

        if config_file is None:
            raise ConfigError("Empty config file")
        # The path is either absolute ot it's relative to the code root
        if not os.path.isabs(config_file):
            config_file = os.path.join(self.script_root, "config",
                                       config_file)
        try:
            os.stat(config_file)
        except OSError:
            self.log.error("Configuration file not found")
            raise

        self.log.debug("Using config file %s", config_file)
        self._file_config = self.load_from_ini(config_file)
        self._config = self.load_config(config_file, self._file_config)

        # Load keys as config attributes
        for key, value in self._config.items():
            setattr(self, key, value)

    def load_config(self, config_file, file_config):
        """
        Basic checks on the config, the loads i into a dictionary
        :param config_file: the path to the configuration file to load
        :param file_config: A dict with the file configuration
        :return:  A dict with the configuration
        """

        config = copy.deepcopy(self.defaults)
        try:
            config.update(file_config['main'])
        except KeyError:
            self.log.error("Config file: %s Missing main section", config_file)
            raise ConfigError
        # Check important sections existence
        try:
            config['promotion_steps_map'] = file_config['promote_from']
        except KeyError:
            self.log.error("Missing promotion_from section")
            raise ConfigError
        for target_name in config['promotion_steps_map']:
            try:
                config['promotion_criteria_map'][target_name] = \
                    file_config[target_name]
            except KeyError:
                self.log.error("Missing criteria section for target %s",
                               target_name)
                raise ConfigError

        # This is done also in the child class, in expand config, but it's
        # really necessary to expand this even in the base class
        config['log_file'] = os.path.expanduser(config['log_file'])

        return config

    def load_from_ini(self, config_path):
        """
        Loads configuration from a INI file.
        :param config_path: the path to the config file
        :return: a dict with the configuration
        """

        cparser = ini_parser.ConfigParser(allow_no_value=True)
        self.log.debug("Using config file %s", config_path)
        try:
            cparser.read(config_path)
        except ini_parser.MissingSectionHeaderError:
            self.log.error("Unable to load config file %s", config_path)
            raise ConfigError

        config = dict(cparser.items())
        return config


class PromoterConfig(PromoterConfigBase):
    """
    This class expands and check the sanity of the config file. Only this
    class should be used by the promoter
    """

    def __init__(self, config_file, overrides=None, filters="all",
                 checks="all"):
        """
        Expands the parent init by adding config expansion, overrides
        handling and sanity checks
        :param config_path: the path to the configuration file to load
        :param overrides: An object with override for the configuration
        """
        super(PromoterConfig, self).__init__(config_file)

        config = {}
        if filters == "all":
            filters = ['overrides', 'expand', 'experimental']
        if 'overrides' in filters:
            config = self.handle_overrides(self._config, overrides)
        if 'expand' in filters:
            config = self.expand_config(config)
        if not self.sanity_check(config, self._file_config, checks=checks):
            self.log.error("Error in configuration file {}"
                           "".format(config_file))
            raise ConfigError

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
                          'promotion_steps_map',
                          'promotion_criteria_map',
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
        api_port = "58080"
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
        config['dlrnauth_username'] = \
            config.pop('username', self.defaults['dlrnauth_username'])
        config['dlrnauth_password'] = os.environ.get('DLRNAPI_PASSWORD', None)

        config['distro_name'] = \
            config.get('distro_name', self.defaults['distro_name']).lower()
        config['distro_version'] = \
            config.get('distro_version',
                       self.defaults['distro_version']).lower()
        config['release'] = \
            config.get('release', self.defaults['release']).lower()

        config['distro'] = "{}{}".format(config['distro_name'],
                                         config['distro_version'])
        config['latest_hashes_count'] = \
            int(config.get('latest_hashes_count',
                           self.defaults['latest_hashes_count']))

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

        config['containers_list_base_url'] = \
            config.get('containers_list_base_url',
                       self.defaults['containers_list_base_url'])

        config['containers_list_path'] = \
            config.get('containers_list_path',
                       self.defaults['containers_list_path'])

        config['log_file'] = os.path.expanduser(config['log_file'])
        config['log_level'] = \
            config.get('log_level', self.defaults['log_level'])
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
        for target_name, job_list in config['promotion_criteria_map'].items():
            criteria = set(list(job_list))
            config['promotion_criteria_map'][target_name] = criteria

        return config

    def sanity_check(self, config, file_config, checks="all"):
        """
        There are several exceptions
        that can block the load
        - Missing main section
        - Missing criteria section for one of the specified candidates
        - Missing jobs in criteria section
        - Missing mandatory parameters
        - Missing password
        """
        conf_ok = True
        mandatory_parameters = [
            "distro_name",
            "distro_version",
            "release",
            "api_url",
            "log_file",
        ]
        if checks == "all":
            checks = ["logs", "parameters", "password", "criteria"]
        if 'logs' in checks:
            try:
                setup_logging('promoter', config['log_level'],
                              config['log_file'])
            except LoggingError:
                conf_ok = False
        for key, value in config.items():
            if key in mandatory_parameters and key not in file_config['main']:
                self.log.warning("Missing parameter in configuration file: %s."
                                 " Using default value: %s"
                                 "", key, value)
        if 'username' not in file_config['main']:
            self.log.warning("Missing parameter in configuration file: "
                             "username. Using default value: %s"
                             "", config['dlrnauth_username'])
        if "password" in checks:
            if config['dlrnauth_password'] is None:
                self.log.error("No dlrnapi password found in env")
                conf_ok = False
        if "criteria" in checks:
            for target_name, job_list in \
                    config['promotion_criteria_map'].items():
                if not job_list:
                    self.log.error("No jobs in criteria for target %s",
                                   target_name)
                    conf_ok = False

        return conf_ok

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
