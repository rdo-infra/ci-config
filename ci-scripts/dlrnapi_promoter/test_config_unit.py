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

from common import setup_logging, close_logging
from config import ConfigCore, PromoterConfig
from collections import OrderedDict


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
            self.config.nonexsting_setting

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
        }
        file_settings = {
            'dlrn_api_host': 'localhost',
            'dlrn_api_port': None,
            'dlrn_api_scheme': 'http',
            'release': 'train',
            'distro_name': 'CeNtOs',
            'distro_version': "7",
            'allowed_clients': "dlrn,containers,qcow",
        }
        cli_settings = {
            'dlrn_api_host': 'trunk.rdoproject.org',
            'dlrn_api_scheme': 'https',
            'dlrn_api_port': 443,
            'release': 'master',
            'distro_version': "8"
        }
        experimental_settings = {
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

    def test_constructor_qcow_server(self):
        self.assertEqual(self.config_normal.qcow_server, "test")

    def test_filter_allowed_clients_string(self):
        expected_list = ['dlrn', 'containers', 'qcow']
        self.assertListEqual(self.config_normal.allowed_clients, expected_list)

    def test_filter_allowed_clients_notstring(self):
        self.assertIsNone(self.config_empty.allowed_clients)

    def test_filter_distro_name_string(self):
        self.assertTrue(self.config_normal['distro_name'], "centos")

    def test_filter_distro_name_notstring(self):
        self.assertIsNone(self.config_empty['distro_name'])

    def test_filter_promotions(self):
        assert False

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


class ConfigCases(unittest.TestCase):

    def setUp(self):
        self.filepaths = {}
        for case, content in test_ini_configurations.items():
            fp, filepath = tempfile.mkstemp(prefix="conf_test_",
                                            suffix=".yaml")
            with os.fdopen(fp, "w") as test_file:
                test_file.write(content)
            self.filepaths[case] = filepath
            self.config_builder = PromoterConfigFactory()

    def tearDown(self):
        for filepath in self.filepaths.values():
            os.unlink(filepath)


class TestConfigFactoryBuild(ConfigCases):

    @patch('logging.Logger.error')
    def test_config_none(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(None)
        mock_log_error.assert_has_calls([
            mock.call("Config file passed can't be None")
        ])

    @patch('logging.Logger.error')
    def test_config_not_found(self, mock_log_error):
        with self.assertRaises(OSError):
            self.config_builder("/does/not/exist")
        mock_log_error.assert_has_calls([
            mock.call("Configuration file not found")
        ])

    @patch('logging.Logger.error')
    def test_load_empty_yaml_config(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(self.filepaths['empty_yaml'])
        mock_log_error.assert_has_calls([
            mock.call("Config file %s does not contain valid data",
                      self.filepaths['empty_yaml'])
        ])

    @patch('logging.Logger.error')
    def test_load_invalid_yaml_config(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(self.filepaths['invalid_yaml'])
        mock_log_error.assert_has_calls([
            mock.call("Unable to load config file %s",
                      self.filepaths['invalid_yaml'])
        ])

    @patch('logging.Logger.error')
    def test_load_not_yaml_config(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(self.filepaths['not_yaml'])
        mock_log_error.assert_has_calls([
            mock.call("Config file %s does not contain valid data",
                      self.filepaths['not_yaml'])
        ])

    @patch('logging.Logger.error')
    def test_load_yaml_file_no_criteria(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(self.filepaths['missing_criteria'])
        mock_log_error.assert_has_calls([
            mock.call("Missing criteria for target %s",
                      'current-tripleo'),
            mock.call('Missing candidate label for target %s',
                      'current-tripleo'),
            mock.call("Error in configuration file %s", self.filepaths[
                'missing_criteria'])
        ])

    @patch('logging.Logger.error')
    def test_load_yaml_file_invalid_log_options(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(self.filepaths['invalid_log'], validate="logs")
        mock_log_error.assert_has_calls([
            mock.call('Invalid log file %s', '/this/does_not_exist'),
            mock.call('Unrecognized log level: %s', 'CATACLYSM'),
            mock.call('Error in configuration file %s',
                      self.filepaths['invalid_log'])
        ])

    @patch('logging.Logger.error')
    def test_load_yaml_file_empty_criteria(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(self.filepaths['empty_criteria'],
                                validate="promotions")
        mock_log_error.assert_has_calls([
            mock.call("Empty criteria for target %s",
                      'current-tripleo'),
            mock.call('Missing candidate label for target %s',
                       'current-tripleo'),
            mock.call("Error in configuration file %s", self.filepaths[
                'empty_criteria'])
        ])

    @patch('logging.Logger.error')
    def test_load_config_missing_promotions(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(self.filepaths['missing_promotions_section'],
                                validate="promotions")
        mock_log_error.assert_has_calls([
            mock.call("Missing promotions section"),
            mock.call("Error in configuration file %s", self.filepaths[
                'missing_promotions_section'])
        ])

    @patch('logging.Logger.error')
    def test_load_config_empty_promotions(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(self.filepaths['empty_promotions_section'])
        mock_log_error.assert_has_calls([
            mock.call("Promotions section is empty"),
            mock.call("No dlrnapi password found in env"),
            mock.call("Error in configuration file %s", self.filepaths[
                'empty_promotions_section'])
        ])

    @patch('logging.Logger.error')
    def test_load_config_missing_pass(self, mock_log_error):
        try:
            del(os.environ["DLRNAPI_PASSWORD"])
        except KeyError:
            pass
        with self.assertRaises(ConfigError):
            self.config_builder(self.filepaths['correct'], validate="password")
        mock_log_error.assert_has_calls([
            mock.call("No dlrnapi password found in env"),
            mock.call("Error in configuration file %s", self.filepaths[
                'correct'])
        ])

    def test_load_correct_yaml_file_verify_params(self):
        self.maxDiff = None
        # Test for load correctness
        os.environ["DLRNAPI_PASSWORD"] = "test"
        config = self.config_builder(self.filepaths['correct'],
                                       validate=['logs', 'promotions'])
        # Test if config keys are there and have a value
        assert hasattr(config, "release"), "Missing mandatory argument"
        assert hasattr(config, "distro_name"), "Missing mandatory argument"
        self.assertIsInstance(config.distro_name, string_types)
        self.assertEqual(config.release, "master")
        self.assertEqual(config.latest_hashes_count, 10)
        # TODO(gcerami) we should also check that ~ in log_file are expanded
        #  to user home, but it's not easy as setting log_file to something
        #  different from /dev/null will need a valid file to write logs to,
        #  and it cannot be in the user home
