import os
import tempfile
import unittest
try:
    # Python3 imports
    from unittest.mock import Mock, patch
    import unittest.mock as mock
except ImportError:
    # Python2 imports
    from mock import Mock, patch
    import mock


from config import ConfigCore


class TestConfigCore(unittest.TestCase):

    def setUp(self):
        low_priority_settings = {
            'simple_lowestlayer': 'simple-lowestlayer',
            # This is also defined in higher precedence layer
            'simple_bothlayers': 'simple-lowestlayer'
        }
        high_priority_settings = {
            'simple_bothlayers': 'simple-highestlayer',
            'jinja_single_samelayer': "{{ simple_bothlayers }}-rendered",
            'jinja_single_crosslayers': "{{ simple_lowestlayer }}-rendered",
            'jinja_recursive_samelayer': "{{ jinja_single_samelayer " \
                                          "}}-recursivelyrendered"
        }
        self.config = ConfigCore(['high_priority', 'low_priority'])
        self.config._layers['high_priority'] = high_priority_settings
        self.config._layers['low_priority'] = low_priority_settings

        class SubConfig(ConfigCore):

            def _constructor_constructed(self):
                return "constructed-value"

            def _filter_filtered(self, value):
                return value.lower()

        self.subconfig = SubConfig(['layer'])
        self.subconfig._layers['layer'] = {'filtered': 'VALUE'}

    def test_get_unknown_attribute(self):
        with self.assertRaises(AttributeError):
            value = self.config.nonexsting_setting

    def test_get_simple_attribute_lowest_layer(self):
        value = self.config.simple_lowestlayer
        self.assertEqual(value, "simple-lowestlayer")
        value = self.config["simple_lowestlayer"]
        self.assertEqual(value, "simple-lowestlayer")

    def test_get_simple_attribute_highest_layer(self):
        value = self.config.simple_bothlayers
        self.assertIn("simple_bothlayers",
                      self.config._layers['low_priority'])
        self.assertIn("simple_bothlayers",
                      self.config._layers['high_priority'])
        self.assertEqual(value, "simple-highestlayer")

    def test_get_jinja_single_samelayer(self):
        value = self.config.jinja_single_samelayer
        self.assertEqual(value, "simple-highestlayer-rendered")

    def test_get_jinja_single_crosslayer(self):
        value = self.config.jinja_single_crosslayers
        self.assertEqual(value, "simple-lowestlayer-rendered")

    def test_jinja_recursive(self):
        value = self.config.jinja_recursive_samelayer
        self.assertEqual(value,
                         "simple-highestlayer-rendered-recursivelyrendered")

    def test_dynamic_constructed(self):
        value = self.subconfig.constructed
        self.assertEqual(value, "constructed-value")

    def test_filtered(self):
        value = self.subconfig.filtered
        self.assertEqual(value, 'value')
