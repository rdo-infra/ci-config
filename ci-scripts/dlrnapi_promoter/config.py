"""
This file contains classes and function to build a configuration object that
can be passed to all the functions in the workfloww
"""
import logging
import pprint

from common import setup_logging, get_root_paths
from jinja2 import Template
from jinja2.nativetypes import native_concat
from collections import OrderedDict


class ConfigCore(object):

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


class PromoterConfig(ConfigCore):

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

    def _filter_promotions(self, promotions):
        if isinstance(promotions, dict):
            _promotions = copy.deepcopy(promotions)
            for target_name, info in promotions.items():
                if 'criteria' in info and not isinstance(info['criteria'], set):
                    info['criteria'] = set(info['criteria'])
            return _promotions
        else:
            return promotions
