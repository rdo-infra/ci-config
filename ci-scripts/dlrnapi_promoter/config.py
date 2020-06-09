"""
This file contains classes and function to build a configuration object that
can be passed to all the functions in the workfloww
"""
import logging
import os
import pprint
from collections import OrderedDict

from jinja2 import Template
from jinja2.nativetypes import native_concat

try:
    # Python 2
    import urlparse
except ImportError:
    # Python 3
    from urllib import parse as urlparse


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
        self._log.debug("Config object configured with layers: %s",
                        ", ".join(layers_list))

    def _dump(self):
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
                self._log.debug("Attribute %s not found in layer %s",
                                attribute_name, source_name)

        try:
            return value
        except UnboundLocalError:
            self._log.warning("Attribute %s not found in layers",
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
    """
    This class implements the Promoter config, using Config Core as a parent
    sets the layers used in promoter configuration and implements contructor
    and filters for the complex configuration variables.
    """

    def __init__(self, default_settings=None, file_settings=None,
                 cli_settings=None, experimental_settings=None):
        """
        Loads the layers into the ConfigCore

        :param default_settings: The default settings
        :param file_settings: settings that come from files inside the
        environment
        :param cli_settings: settings that come from command lines
        :param experimental_settings: settings that are for experimental use
        """
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
        self._log.debug("Initialized")

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
        version = self['distro_version']
        release = self['release']
        url_port = None
        endpoint = None

        distro_endpoint = distro

        if version == '8':
            distro_endpoint += version
        release_endpoint = release
        if release == "master":
            release_endpoint = "master-uc"
        if distro_endpoint is not None and release_endpoint is not None:
            endpoint = "api-{}-{}".format(distro_endpoint,
                                          release_endpoint)
        if port is None or (scheme == "http" and port == 443) \
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
                print(type(info['criteria']))
                if 'criteria' in info and not isinstance(info['criteria'], set):
                    self._log.debug("Transforming criteria into a set")
                    info['criteria'] = set(info['criteria'])
        else:
            self._log.debug("Promotions is not a dict")

        return promotions
