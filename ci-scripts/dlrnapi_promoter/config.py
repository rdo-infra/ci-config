"""
This file contains classes and function to build a configuration object that
can be passed to all the functions in the workfloww
"""
import logging
from collections import OrderedDict

from jinja2 import Template
from jinja2.nativetypes import native_concat


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
