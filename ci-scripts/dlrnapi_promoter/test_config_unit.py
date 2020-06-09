import os
import unittest

try:
    # Python3 imports
    import unittest.mock as mock
    from unittest.mock import patch
except ImportError:
    # Python2 imports
    from mock import patch
    import mock

from collections import OrderedDict

from common import close_logging, setup_logging
from config import ConfigCore, PromoterConfig


class TestConfigCore(unittest.TestCase):
    """
    Test considers as unit the entire class.
    """

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
            'jinja_recursive_samelayer': ("{{ jinja_single_samelayer }}"
                                          "-recursivelyrendered")
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
            _ = self.config.nonexsting_setting

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


class TestPromoterConfig(unittest.TestCase):

    def setUp(self):
        setup_logging("promoter", 10)
        default_settings = {
            'dlrn_api_host': None,
            'dlrn_api_port': None,
            'dlrn_api_scheme': None,
            'release': None,
            'distro_name': None,
            'distro_version': None,
            'allowed_clients': None,
            'promotions': None,
        }
        file_settings = {
            'dlrn_api_host': 'localhost',
            'dlrn_api_port': None,
            'dlrn_api_scheme': 'http',
            'release': 'train',
            'distro_name': 'CeNtOs',
            'distro_version': "7",
            'allowed_clients': "dlrn_client,registries_client,qcow_client",
            'promotions': {
                'target-label': {
                    'candidate_label': 'candidate-label',
                    'criteria': [
                        'job1',
                        'job2'
                    ]
                }
            },
            'overcloud_images': {
                'qcow_servers': {
                    'localhost': {
                        'address': 'localhost',
                        'root': '/var/www/images'
                    }
                }
            }
        }
        cli_settings = {
            'dlrn_api_host': 'trunk.rdoproject.org',
            'dlrn_api_scheme': 'https',
            'dlrn_api_port': 443,
            'release': 'master',
            'distro_version': "8",
            'default_qcow_server': 'localhost'
        }
        self.config_empty = PromoterConfig(default_settings=default_settings)
        self.config_normal = PromoterConfig(default_settings=default_settings,
                                            file_settings=file_settings)
        self.config_special = PromoterConfig(default_settings=default_settings,
                                             file_settings=file_settings,
                                             cli_settings=cli_settings)

    def tearDown(self):
        close_logging("promoter")

    def test_base_instance(self):
        assert hasattr(self.config_normal, "_layers")
        self.assertIsInstance(self.config_normal._layers, OrderedDict)
        self.assertIn("cli", self.config_normal._layers)
        self.assertIn("file", self.config_normal._layers)
        self.assertIn("default", self.config_normal._layers)
        self.assertIn("experimental", self.config_normal._layers)
        self.assertIsInstance(self.config_normal._layers['cli'], dict)
        self.assertIsInstance(self.config_normal._layers['file'], dict)
        self.assertIsInstance(self.config_normal._layers['default'], dict)
        self.assertIsInstance(self.config_normal._layers['experimental'], dict)

    def test_constructor_dlrnauth_password_present(self):
        os.environ["DLRNAPI_PASSWORD"] = "test"
        self.assertEqual(self.config_empty.dlrnauth_password, "test")
        del(os.environ['DLRNAPI_PASSWORD'])

    def test_constructor_dlrnauth_password_absent(self):
        try:
            del(os.environ['DLRNAPI_PASSWORD'])
        except KeyError:
            pass
        self.assertIsNone(self.config_empty.dlrnauth_password)

    def test_constructor_qcow_server_default(self):
        server_info = self.config_special.qcow_server
        self.assertIsInstance(server_info, dict)
        self.assertIn('address', server_info)
        self.assertIn('root', server_info)
        self.assertEqual(server_info['address'], "localhost")
        self.assertEqual(server_info['root'], "/var/www/images")

    def test_constructor_qcow_server_notexisting(self):
        with self.assertRaises(AttributeError):
            _ = self.config_empty.qcow_server

    def test_filter_allowed_clients_string(self):
        expected_list = ['dlrn_client', 'registries_client', 'qcow_client']
        self.assertListEqual(self.config_normal.allowed_clients, expected_list)

    def test_filter_allowed_clients_notstring(self):
        self.assertIsNone(self.config_empty.allowed_clients)

    def test_filter_distro_name_string(self):
        self.assertTrue(self.config_normal['distro_name'], "centos")

    def test_filter_distro_name_notstring(self):
        self.assertIsNone(self.config_empty['distro_name'])

    def test_filter_promotions_notdict(self):
        self.assertIsNone(self.config_empty.promotions)

    def test_filter_promotions_dict(self):
        promotions = self.config_normal.promotions
        for __, info in promotions.items():
            self.assertIsInstance(info['criteria'], set)

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    def test_get_dlrn_api_url_normal_cases(self,
                                           mock_log_debug,
                                           mock_log_error):
        expected_url = "http://localhost/api-centos-train"
        api_url = self.config_normal.api_url
        self.assertEqual(api_url, expected_url)
        mock_log_debug.assert_has_calls([
            mock.call("Assigning api_url %s", expected_url)
        ])
        self.assertFalse(mock_log_error.called)

    @patch('logging.Logger.error')
    def test_get_dlrn_api_url_empty(self, mock_log_error):
        api_url = self.config_empty.api_url
        expected_url = None
        self.assertEqual(api_url, expected_url)
        mock_log_error.assert_has_calls([
            mock.call("No valid API url found")
        ])

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    def test_get_dlrn_api_url_special_cases(self,
                                            mock_log_debug,
                                            mock_log_error):
        expected_url = "https://trunk.rdoproject.org/api-centos8-master-uc"
        api_url = self.config_special.api_url
        self.assertEqual(api_url, expected_url)
        mock_log_debug.assert_has_calls([
            mock.call("Assigning api_url %s", expected_url)
        ])
        self.assertFalse(mock_log_error.called)

    def test_constructor_namespace_ussuri(self):
        self.config_special.release = "ussuri"
        self.assertEqual(self.config_special.source_namespace, "tripleou")
        self.assertEqual(self.config_special.target_namespace, "tripleou")

    def test_constructor_namespace_notussuri(self):
        self.assertEqual(self.config_special.source_namespace, "tripleomaster")
        self.assertEqual(self.config_special.target_namespace, "tripleomaster")
