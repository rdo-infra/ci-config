"""
This file contains classes and function to build a configuration object that
can be passed to all the functions in the workfloww
"""
import copy

import common
import logging
import os
import pprint
import yaml

from common import setup_logging, get_root_paths
from jinja2 import Template
from jinja2.nativetypes import native_concat
from collections import OrderedDict


class ConfigError(Exception):
    pass


<<<<<<< HEAD
class Config(object):
||||||| parent of 32493d8... [WIP] Promoter: add support multiple configuration environments
class PromoterConfig(object):
=======
<<<<<<< HEAD
class PromoterConfig(object):
>>>>>>> 32493d8... [WIP] Promoter: add support multiple configuration environments

    _log = logging.getLogger("promoter")

    def __init__(self, layers_list):
        """
        Initializes the layers in a ordered dict
        :param layers_list: the list of layers in the configuration,
        high priority first. The list cannot be changed.
        """
        self._layers = OrderedDict()
        for layer_name in layers_list:
            self._layers[layer_name] = {}

    def _fill_layer_settings(self, layer_name, settings):
        """
        Allow access to the _layers data structure
        :param layer_name: The layer name to fill
        :param settings: A dict with the settings for the layer
        :return: None
        """
        self._layers[layer_name] = settings

    def _construct_value(self, attribute_name):
        """
        Generates the constructor name from the attribute name, and tries to
        call it.
        :param attribute_name: The name of the attribute whose value needs
        construction
        :return: The generated value if the constructor exists. raises
        AttributeError in case of any error
        """
        constructor_name = "_constructor_{}".format(attribute_name)
        try:
            constructor = self.__getattribute__(constructor_name)
        except AttributeError:
            self._log.error("No constructor for attribute %s", attribute_name)
            raise AttributeError

        self._log.debug("Running constructor for attribute %s",
                       attribute_name)
        try:
            return constructor()
        except Exception as exc:
            self._log.error("The constructor for attribute %s generated an "
                           "error, no value can be constructed")
            self._log.exception(exc)
            raise AttributeError

    def _search_layers(self, attribute_name):
        """
        Performs the simple search for the attribute name, on all layers,
        highest priority to lowest priority
        :param attribute_name: The name of the attribute to search
        :return: The value of the attribute or AttributeError if not found
        """
        for source_name, source in self.__getattribute__('_layers').items():
            try:
                value = source[attribute_name]
                self._log.debug("Getting attribute %s from layer '%s' ",
                                attribute_name, source_name)
                break
            except KeyError:
                pass

        try:
            return value
        except UnboundLocalError:
            raise AttributeError

    def _filter(self, attribute_name, value):
        """
        Generates the filter name from the attribute name and tried to call
        it with the value as parameter
        :param attribute_name: THe name of the attribute whose value need
        filtering
        :param value: The value of the attribute
        :return: The filtered value of the attribute or AttributeError if the
        filter fails
        """
        filter_name = "_filter_{}".format(attribute_name)
        try:
            filter_method = self.__getattribute__(filter_name)
        except AttributeError:
            return value

        self._log.debug("Running filter for attribute %s",
                       attribute_name)
        try:
            return filter_method(value)
        except Exception as exc:
            self._log.error("The filter for attribute %s generated an "
                            "error, no value can be constructed")
            self._log.exception(exc)
            raise AttributeError

    def _get_value(self, attribute_name):
        """
        High level method to drive the extraction/creation of a value from
        the attribute name.
        :param attribute_name: The name of the attribute whose value we want
        to know
        :return: The value or AttributeError if no value can be found or
        constructed
        """
        try:
            return self._search_layers(attribute_name)
        except AttributeError:
            self._log.debug("Attribute %s not found in layers", attribute_name)
            try:
                return self._construct_value(attribute_name)
            except AttributeError:
                self._log.error("No attribute %s in config", attribute_name)
                raise AttributeError("No setting '{}' found"
                                     "".format(attribute_name))

    def _render(self, value):
        """
        Renders a string value that may contain a jinja template.
        :param value: The string with the possible template
        :return: The rendered string if it's a template, value otherwise
        """
        template = Template(value)
        # We can't call template.render directly in our case, as the render
        # will try to build a static dict from this object, and the dict will
        # be empty as we have no static values.
        # So we use low level API, passing shared=True and locals=False to
        # the context for the same reason as above.
        value = native_concat(template.root_render_func(
            template.new_context(vars=self, shared=True, locals=None)))
        return value

    def __getattr__(self, attribute_name):
        """
        Drives any attribute access to the configuration. All
        config.attribute start generation here.
        The method tries to get a value then filters it and renders it when
        found
        :param attribute_name:
        :return: The value of the attribute or AttributeError if no value is
        available with any mean possible
        """
        value = self._get_value(attribute_name)
        value = self._filter(attribute_name, value)

        if isinstance(value, str):
            return self._render(value)
        else:
            return value

    def __getitem__(self, attribute_name):
        """
        config[item] is the same as config.item.
        This method is needed for templating, as jinja2 expects
        the data structure the act like a dict
        :param attribute_name:
        :return: The value of the attribute
        """
        return self.__getattr__(attribute_name)

    def __contains__(self, attribute_name):
        """
        This method is needed for templating, as jinja2 expects
        the data structure the act like a dict
        :param attribute_name: The name of the attribute to check
        :return: A bool, true if name is in config, false otherwise
        """
        try:
            self._get_value(attribute_name)
            return True
        except AttributeError:
            return False


class PromoterConfig(Config):

    def __init__(self, default_settings=None, file_settings=None,
                 cli_settings=None, experimental_settings=None):
        super(PromoterConfig, self).__init__(['cli', 'file', 'default',
                                              'experimental'])
        if cli_settings is None:
            cli_settings = {}
        if file_settings is None:
            file_settings = {}
        if default_settings is None:
            default_settings = {}
        if experimental_settings is None:
            experimental_settings = {}
        self._layers["cli"] = cli_settings
        self._layers['file'] = file_settings
        self._layers['default'] = default_settings
        self._layers['experimental'] = experimental_settings

    # Constructors

    def _constructor_dlrnauth_password(self):
        return os.environ.get('DLRNAPI_PASSWORD', None)

    def _constructor_qcow_server(self):
        return self['overcloud_images']['qcow_servers'][
            self.default_qcow_server]

    def _constructor_api_url(self):
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

    def _filter_allowed_clients(self, allowed_clients):
        return allowed_clients.split(',')

    def _filter_distro_name(self, distro_name):
        return distro_name.lower()

<<<<<<< HEAD
    def _filter_promotions(self, promotions):
<<<<<<< HEAD
        if isinstance(promotions, dict):
            _promotions = copy.deepcopy(promotions)
            for target_name, info in promotions.items():
                if 'criteria' in info and not isinstance(info['criteria'], set):
                    info['criteria'] = set(info['criteria'])
            return _promotions
        else:
            return promotions
||||||| parent of 3cb5699... [WIP] Promoter: add support multiple configuration environments
        for target_name, info in promotions.items():
            if not isinstance(info['criteria'], set):
                info['criteria'] = set(info['criteria'])
=======
||||||| parent of 32493d8... [WIP] Promoter: add support multiple configuration environments
    def set_filter_promotions(self, promotions):
=======
<<<<<<< HEAD
    def set_filter_promotions(self, promotions):
>>>>>>> 32493d8... [WIP] Promoter: add support multiple configuration environments
        for target_name, info in promotions.items():
            if not isinstance(info['criteria'], set):
                info['criteria'] = set(info['criteria'])
>>>>>>> 3cb5699... [WIP] Promoter: add support multiple configuration environments


class PromoterConfigFactory(object):
||||||| parent of b91ae84... [WIP] Promoter: add support multiple configuration environments
class PromoterConfigGenerator(object):
=======
class PromoterConfigGenerator(object):
||||||| parent of f19bd79... [WIP] Promoter: add support multiple configuration environments
class PromoterConfigBase(object):
=======
def load_defaults(config_root_path):
    defaults_path = os.path.join(config_root_path, "defaults.yaml")
    with open(defaults_path) as defaults_file:
        defaults = yaml.safe_load(defaults_file)

    return defaults


class PromoterConfigBase(object):
>>>>>>> f19bd79... [WIP] Promoter: add support multiple configuration environments
>>>>>>> b91ae84... [WIP] Promoter: add support multiple configuration environments
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
        'promotions': None,
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
<<<<<<< HEAD

||||||| parent of f19bd79... [WIP] Promoter: add support multiple configuration environments
=======
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
>>>>>>> f19bd79... [WIP] Promoter: add support multiple configuration environments
    log = logging.getLogger("promoter")

<<<<<<< HEAD
    def __init__(self, filters="all", validate="all"):
||||||| parent of f19bd79... [WIP] Promoter: add support multiple configuration environments
    def __init__(self, config_path, sanity_checks="all"):
=======
<<<<<<< HEAD
    def __init__(self, config_path, sanity_checks="all"):
||||||| parent of 6188269... [WIP] Promoter: add support multiple configuration environments
    def __init__(self, config_file):
=======
    def __init__(self, config_rel_path, config_root=None):
>>>>>>> 6188269... [WIP] Promoter: add support multiple configuration environments
>>>>>>> f19bd79... [WIP] Promoter: add support multiple configuration environments
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
<<<<<<< HEAD
||||||| parent of f19bd79... [WIP] Promoter: add support multiple configuration environments
        self.log.debug("Config file passed: %s", config_path)
=======
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
>>>>>>> f19bd79... [WIP] Promoter: add support multiple configuration environments
        self.log.debug("Git root %s", self.git_root)
<<<<<<< HEAD
        self.log.debug("Script root %s", self.git_root)
||||||| parent of b91ae84... [WIP] Promoter: add support multiple configuration environments
=======
        self.defaults = load_defaults(self.config_root)
>>>>>>> b91ae84... [WIP] Promoter: add support multiple configuration environments

<<<<<<< HEAD
    def __call__(self, config_path, cli_settings=None, validate="all"):
        file_settings = self.load_file_settings(config_path)
        experimental_path = os.path.join(self.script_root,
                                         "promoter_defaults_experimental.yaml")
        experimental_settings = self.load_file_settings(experimental_path)
||||||| parent of b91ae84... [WIP] Promoter: add support multiple configuration environments
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
=======
<<<<<<< HEAD
    def __call__(self, config_path, filters="all", validate="all"):
        self.log.debug("Config file passed: %s", config_path)
||||||| parent of f19bd79... [WIP] Promoter: add support multiple configuration environments
=======
<<<<<<< HEAD
>>>>>>> f19bd79... [WIP] Promoter: add support multiple configuration environments
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
>>>>>>> b91ae84... [WIP] Promoter: add support multiple configuration environments

<<<<<<< HEAD
        config = PromoterConfig(default_settings=self.defaults,
                                file_settings=file_settings,
                                cli_settings=cli_settings,
                                experimental_settings=experimental_settings)
||||||| parent of b91ae84... [WIP] Promoter: add support multiple configuration environments
        config = self.load_config(config_path)
=======
<<<<<<< HEAD
        config = self.load_config(config_path)
||||||| parent of f19bd79... [WIP] Promoter: add support multiple configuration environments
        self._config = self.load_config(config_path)
=======
<<<<<<< HEAD
        self._config = self.load_config(config_path)
>>>>>>> f19bd79... [WIP] Promoter: add support multiple configuration environments
>>>>>>> b91ae84... [WIP] Promoter: add support multiple configuration environments

        if not self.validate(config, checks=validate):
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
        :param config: A PromoterConfig instance to check
        :param checks: a comma separated list of checks to perform
        :return: A boolean, True if the validation was successful,
        false otherwise
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
                self.log.error("Invalid log file %s", config.log_file)
                conf_ok = False
            try:
                getattr(logging, config.log_level)
            except AttributeError:
                self.log.error("Unrecognized log level: %s",
                               config['log_level'])
                conf_ok = False

        if "promotions" in checks:
            try:
                promotions = config.promotions
            except AttributeError:
                self.log.error("Missing promotions section")
                conf_ok = False

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
            if config.dlrnauth_password is None:
                self.log.error("No dlrnapi password found in env")
                conf_ok = False

        return conf_ok

<<<<<<< HEAD
||||||| parent of b91ae84... [WIP] Promoter: add support multiple configuration environments
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
=======
    def launch_filters(self, config, filters="all"):

        if not filters:
            return config

<<<<<<< HEAD
||||||| parent of f19bd79... [WIP] Promoter: add support multiple configuration environments
    def __init__(self, config_path, overrides=None, filters="all",
                 sanity_checks="all"):
        """
        Expands the parent init by adding config expansion, overrides
        handling and sanity checks
        :param config_path: the path to the configuration file to load
        :param overrides: An object with override for the configuration
        """
        super(PromoterConfig, self).__init__(config_path,
                                             sanity_checks=sanity_checks)

        config = {}
=======
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
>>>>>>> f19bd79... [WIP] Promoter: add support multiple configuration environments
        if filters == "all":
            filters = ['overrides', 'expand']
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
>>>>>>> b91ae84... [WIP] Promoter: add support multiple configuration environments
