"""
This file contains classes and function to build a configuration object that
can be passed to all the functions in the workfloww
"""
import logging
import os
import pprint
from collections import OrderedDict

import yaml
from jinja2 import Template
from jinja2.nativetypes import native_concat
from promoter.common import get_root_paths, setup_logging

try:
    # Python 2
    import urlparse
except ImportError:
    # Python 3
    from urllib import parse as urlparse

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError
try:
    PermissionError
except NameError:
    PermissionError = IOError


class ConfigError(Exception):
    pass


class ConfigCore(object):
    _log = logging.getLogger("promoter")

    def __init__(self, layers_list, verbose=False):
        """
        Initializes the layers in a ordered dict
        :param layers_list: the list of layers in the configuration,
        high priority first. The list cannot be changed.
        """
        self._layers = OrderedDict()
        for layer_name in layers_list:
            if layer_name:
                self._layers[layer_name] = {}
        self._log.debug("Config object configured with layers: %s",
                        ", ".join(self._layers.keys()))
        # As config is used everywhere multiple times, some debug message may
        # flood the logs. We enable them only when we really want to trace
        # the config engine
        self._verbose = verbose

    def _dump_layers(self):
        pprint.pprint(self._layers)

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
                            "error, no value can be constructed",
                            attribute_name)
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
            if not hasattr(source, '__getitem__'):
                self._log.warning("Unable to search on layer %s",
                                  source_name)
                continue
            try:
                value = source[attribute_name]
                if self._verbose:
                    self._log.debug("Getting attribute %s from layer '%s' ",
                                    attribute_name, source_name)
                break
            except KeyError:
                if self._verbose:
                    self._log.debug("Attribute %s not found in layer %s",
                                    attribute_name, source_name)

        try:
            return value
        except UnboundLocalError:
            if self._verbose:
                self._log.debug("Attribute %s not found in layers",
                                attribute_name)
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

        if self._verbose:
            self._log.debug("Running filter for attribute %s", attribute_name)

        try:
            return filter_method(value)
        except Exception as exc:
            self._log.error("The filter for attribute %s generated an "
                            "error, no value can be constructed",
                            attribute_name)
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

        # native concat renders empty strings as None ...
        if not value:
            value = ''
        # native concat returns int for string that contains only numbers
        # so we force to return a string
        return str(value)

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

    # TODO: I could make two different cases here:
    #  config['attr'] will always retrieve the config following the process
    #  no matter what the attributes in the object are.
    #  config.attr will try existing attribute if found first
    def __setitem__(self, attribute_name, value):
        """
        config[item] is the same as config.item.
        This method emulates dict assignment with attribute setting
        It should be used carefully it as completely bypasses all methods
        :param attribute_name: the attribute name
        :param value: the value
        :return: None
        """
        setattr(self, attribute_name, value)

    def __getitem__(self, attribute_name):
        """
        config[item] is the same as config.item.
        This method is needed for templating, as jinja2 expects
        the data structure the act like a dict
        :param attribute_name:
        :return: The value of the attribute
        """
        return getattr(self, attribute_name)

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


class PromoterConfig(ConfigCore):
    """
    This class implements the Promoter config, using Config Core as a parent
    sets the layers used in promoter configuration and implements constructor
    and filters for the complex configuration variables.
    """

    def __init__(self, global_defaults=None, environment_defaults=None,
                 release_settings=None, cli_settings=None, extra_settings=None):
        """
        Loads the layers into the ConfigCore

        :param environment_defaults: The default settings in the environment
        :param global_defaults: The default settings for all environments
        :param release_settings: settings that come from the release files
        inside the environment
        :param cli_settings: settings that come from command lines
        :param extra_settings: settings that are for experimental use,
        and are usually passed intentionally to the config
        """
        super(PromoterConfig, self).__init__(['extra', 'cli', 'release',
                                              'environment_defaults',
                                              'global_defaults'])
        if extra_settings is None:
            extra_settings = {}
        if cli_settings is None:
            cli_settings = {}
        if release_settings is None:
            release_settings = {}
        if environment_defaults is None:
            environment_defaults = {}
        if global_defaults is None:
            global_defaults = {}

        self._layers["extra"] = extra_settings
        self._layers["cli"] = cli_settings
        self._layers['release'] = release_settings
        self._layers['environment_defaults'] = environment_defaults
        self._layers['global_defaults'] = global_defaults

        self._log.debug("Initialized Promoter config layers")

    # Constructors

    def _constructor_dlrnauth_password(self):
        """
        Returns the password, stored as environment variable.
        :return: A string with the password, or None if not found
        """
        return os.environ.get('DLRNAPI_PASSWORD', None)

    def _constructor_qcow_server(self):
        """
        Extract the server dict from the options
        :return: A dict with the server info
        """

        # pylint: disable=E1126
        return self['overcloud_images']['qcow_servers'][
            self.default_qcow_server]

    def _constructor_promoter_user(self):
        return os.environ.get('USER', None)

    def _constructor_api_url(self):
        """
        API url is the wild west of exceptions. This method builds the api
        url taking into account all these exception
        :return: A string with the url, may be empty.
        """
        host = self['dlrn_api_host']
        port = self['dlrn_api_port']
        scheme = self['dlrn_api_scheme']
        distro = self['distro_name']
        version = str(self['distro_version'])
        release = self['release']
        url_port = None
        endpoint = ''

        distro_endpoint = distro

        if version == '8':
            distro_endpoint += version
        release_endpoint = release

        try:
            endpoint = self['dlrn_api_endpoint']
        except AttributeError:
            if release == "master":
                release_endpoint = "master-uc"
            if distro_endpoint is not None and release_endpoint is not None:
                endpoint = "api-{}-{}".format(distro_endpoint,
                                              release_endpoint)

        if port in [None, ""] or (scheme == "http" and port == 443) \
                or (scheme == "https" and port == 443):
            url_port = ""
        else:
            url_port = ":{}".format(port)

        if not host and not port:
            url_hostport = ""
        else:
            url_hostport = "{}{}".format(host, url_port)

        url_elements = [None] * 6
        url_elements[0] = scheme
        url_elements[1] = url_hostport
        url_elements[2] = endpoint
        url = urlparse.urlunparse(url_elements)
        if isinstance(url, bytes):
            url = url.decode("UTF-8")
        if not url:
            url = None

        if url is None:
            self._log.error("No valid API url found")
        else:
            self._log.debug("Assigning api_url %s", url)
        return url

    def __common_constructor_namespace(self):
        if self.release == "ussuri":
            namespace = "tripleou"
        else:
            namespace = "tripleo{}".format(self.release)

        return namespace

    def _constructor_source_namespace(self):
        return self.__common_constructor_namespace()

    def _constructor_target_namespace(self):
        return self.__common_constructor_namespace()

    # filters

    def _filter_scenes(self, scenes):
        if isinstance(scenes, str):
            return scenes.split(',')
        else:
            return scenes

    def _filter_allowed_clients(self, allowed_clients):
        """
        Transform a comma separated string list into a list
        :param allowed_clients: The string with all clients allowed to run
        :return: A list
        """
        if isinstance(allowed_clients, str):
            return allowed_clients.split(',')
        else:
            self._log.error("allowed_clients is not a string")
            return allowed_clients

    def _filter_distro_name(self, distro_name):
        """
        Make the distro name lowercase
        :param distro_name: The string with distro name
        :return: The string with the lowercase name or None if it's not a string
        """
        if isinstance(distro_name, str):
            return distro_name.lower()
        else:
            self._log.error("distro_name is not a string")
            return None

    def _filter_promotions(self, promotions):
        """
        On each promotion stop information, transform the list of jobs in
        criteria into a set
        :param promotions: The dict with the promotions steps
        :return: The same dict with criterias as set
        """
        if isinstance(promotions, dict):
            self._log.debug("Promotions is a dict")
            for target_name, info in promotions.items():
                try:
                    if isinstance(info['criteria'], set):
                        self._log.debug("criteria is already a set")
                    else:
                        self._log.debug("Transforming criteria into a set")
                        info['criteria'] = set(info['criteria'])

                except KeyError:
                    self._log.debug("No criteria info")

        else:
            self._log.debug("Promotions is not a dict")

        return promotions

    # Commenting because it fail tests
    #  def _filter_containers(self, containers):
    #    pass


class PromoterConfigFactory(object):
    """
    This class builds a singleton object to be passed to all the other
    functions in the workflow.
    The base class should be only used for testing as it just performs the
    basic loading.
    """

    log = logging.getLogger("promoter")

    def __init__(self, config_class=PromoterConfig, **kwargs):
        """
        Initialize the config object loading from ini file
        :param config_path: the path to the configuration file to load
        :param validate: A comma separated list of checks for the config
        file
        """
        # Initial log setup
        setup_logging("promoter", logging.DEBUG,
                      log_file=kwargs.get(
                          'log_file',
                          '~/web/promoter_logs/centos8_master.log'))
        self.git_root = None
        self.script_root = None
        self.git_root, self.script_root = get_root_paths(self.log)
        self.log.debug("Git root %s", self.git_root)
        self.log.debug("Script root %s", self.git_root)
        self.rel_roots_map = {
            "global_defaults": os.path.join(self.script_root,
                                            "config_environments"),
            "environments_pool": os.path.join(self.script_root,
                                              "config_environments"),
        }

        self.global_defaults = self.load_yaml_config("global_defaults",
                                                     "global_defaults.yaml")
        self.global_defaults['git_root'] = self.git_root
        self.global_defaults['script_root'] = self.script_root
        self.config_class = config_class

    def __call__(self, environment_root, release_settings_path, cli_args=None,
                 validate="all"):

        # set environment root as root for all other files
        environment_root_path = \
            self.convert_path_rel_to_abs("environments_pool", environment_root)
        self.validate_path(environment_root_path, path_name="Environment root")

        self.rel_roots_map['environment'] = environment_root_path

        layers = {
            'global_defaults': self.global_defaults,
            'environment_defaults': self.load_yaml_config("environment",
                                                          "defaults.yaml")
        }

        try:
            release_settings = self.load_yaml_config("environment",
                                                     release_settings_path)
            layers['release_settings'] = release_settings
        except ConfigError:
            pass

        if cli_args:
            layers['cli_settings'] = cli_args.__dict__
            try:
                extra_settings = self.load_yaml_config("environment",
                                                       cli_args.extra_settings)
                layers['extra_settings'] = extra_settings
            except AttributeError:
                pass

        config = self.config_class(**layers)
        if not self.validate(config, checks=validate):
            self.log.error("Error in configuration")
            raise ConfigError

        return config

    def convert_path_rel_to_abs(self, default_root_name, config_path):
        """
        Convert relative paths to absolute path, with root according to
        the relative map.
        if None is relative the the current working directory
        # The path is either absolute ot it's relative to the config
        # environment root
        :return:
        """
        if not config_path:
            return config_path

        if os.path.isabs(config_path):
            self.log.debug("%s is an absolute path, not "
                           "converting" % config_path)
            return config_path

        _config_path = config_path
        default_root = self.rel_roots_map[default_root_name]
        config_path = os.path.join(default_root, config_path)
        self.log.debug("Converted %s to %s", _config_path, config_path)
        return config_path

    def validate_path(self, path, path_name='Path'):
        self.log.debug("%s: %s", path_name, path)
        if not path:
            self.log.error("%s can't be empty", path_name)
            raise ConfigError
        try:
            os.stat(path)
        except OSError:
            self.log.error("%s %s not found", path_name, path)
            raise

    def load_yaml_config(self, default_root_name, config_path):
        """
        Loads configuration from a yaml file.
        :param config_path: the path to the config file
        :return: a dict with the configuration
        """
        config_path = self.convert_path_rel_to_abs(default_root_name,
                                                   config_path)
        self.validate_path(config_path)
        self.log.debug("Using config file %s", config_path)
        with open(config_path) as config_file:
            try:
                config = yaml.safe_load(config_file)
            except yaml.YAMLError as exc:
                self.log.error("Not a valid yaml: %s", config_path)
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

        validation_errors = []
        if checks == "all":
            checks = ["logs", "password", "promotions"]

        if 'logs' in checks:
            try:
                with open(os.path.expanduser(config.log_file), "w"):
                    pass
            except (FileNotFoundError, PermissionError):
                validation_errors.append("Invalid log file "
                                         "{}".format(config.log_file))
            try:
                getattr(logging, config.log_level)
            except AttributeError:
                validation_errors.append("Unrecognized log level: {}"
                                         "".format(config['log_level']))

        if "promotions" in checks:
            try:
                promotions = config.promotions
                if not promotions:
                    validation_errors.append("Empty promotions section")
                else:
                    for target_name, info in promotions.items():
                        if 'criteria' not in info:
                            validation_errors.append(
                                "Missing criteria for target "
                                "{}".format(target_name))
                        if 'criteria' in info and not info['criteria']:
                            validation_errors.append(
                                "Empty criteria for target {}"
                                "".format(target_name))
                        if 'candidate_label' not in info:
                            validation_errors.append(
                                "Missing candidate label for "
                                "target {}"
                                "".format(target_name))

            except AttributeError:
                validation_errors.append("Missing promotions section")

        if "password" in checks:
            if config.dlrnauth_password is None:
                validation_errors.append("No dlrnapi password found in env")

        if validation_errors:
            self.log.error("Validation Error: %s", ", ".join(validation_errors))
            return False

        self.log.info("Validation Successful")
        return True
