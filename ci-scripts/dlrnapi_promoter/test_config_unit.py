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

import pytest
from six import string_types

from collections import OrderedDict
from config import ConfigError, PromoterConfigFactory, PromoterConfig, Config
from test_unit_fixtures import test_ini_configurations



class TestConfigInstance(unittest.TestCase):
    pass

class TestConfig(unittest.TestCase):

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
        self.config = Config(['high_priority', 'low_priority'])
        self.config._layers['high_priority'] = high_priority_settings
        self.config._layers['low_priority'] = low_priority_settings

        class SubConfig(Config):

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


class TestPromoterConfigInstance(unittest.TestCase):

    def test_base_instance(self):
        config = PromoterConfig()
        assert hasattr(config, "settings")
        self.assertIsInstance(config.settings, OrderedDict)
        self.assertIn("cli", config.settings)
        self.assertIn("file", config.settings)
        self.assertIn("default", config.settings)
        self.assertIn("experimental", config.settings)
        self.assertIsInstance(config.settings['cli'], dict)
        self.assertIsInstance(config.settings['file'], dict)
        self.assertIsInstance(config.settings['default'], dict)
        self.assertIsInstance(config.settings['experimental'], dict)


class TestPromoterConfig(unittest.TestCase):
    pass


class CorrectCase(unittest.TestCase):

    def setUp(self):
        self.filepaths = {}
        for case, content in test_ini_configurations.items():
            fp, filepath = tempfile.mkstemp(prefix="conf_test_", suffix=".yaml")
            with os.fdopen(fp, "w") as test_file:
                test_file.write(content)
            self.filepaths[case] = filepath

    def tearDown(self):
        for filepath in self.filepaths.values():
            os.unlink(filepath)


class TestConfigFactoryInstance(unittest.TestCase):

    @patch('logging.Logger.debug')
    def test_base_instance(self, mock_log_debug):
        config_builder = PromoterConfigFactory()
        self.assertIsNotNone(config_builder.git_root)
        self.assertIsNotNone(config_builder.script_root)
        mock_log_debug.assert_has_calls([
            mock.call("Git root %s", mock.ANY),
            mock.call("Script root %s", mock.ANY)
        ])


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
                      'current-tripleo')
        ])

    @patch('logging.Logger.error')
    def test_load_yaml_file_invalid_log(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(self.filepaths['invalid_log'])
        mock_log_error.assert_has_calls([
            mock.call("Missing criteria for target %s",
                      'current-tripleo')
        ])

    @patch('logging.Logger.error')
    def test_load_yaml_file_empty_criteria(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(self.filepaths['empty_criteria'])
        mock_log_error.assert_has_calls([
            mock.call("Empty criteria for target %s",
                      'current-tripleo')
        ])

    @patch('logging.Logger.error')
    def test_load_config_missing_promotions(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(self.filepaths['missing_promotions_section'])
        mock_log_error.assert_has_calls([
            mock.call("Promotions section is empty"),
            mock.call("No dlrnapi password found in env"),
            mock.call("Error in configuration file %s", self.filepaths[
                'missing_promotions_section'])
        ])

    @patch('logging.Logger.error')
    def test_load_config_missing_pass(self, mock_log_error):
        try:
            del(os.environ["DLRNAPI_PASSWORD"])
        except KeyError:
            pass
        with self.assertRaises(ConfigError):
            self.config_builder(self.filepaths['correct'])
        mock_log_error.assert_has_calls([
            mock.call("Promotions section is empty"),
            mock.call("No dlrnapi password found in env"),
            mock.call("Error in configuration file %s", self.filepaths[
                'missing_promotions_section'])
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


# FIXME: python2 has no unittest.assertLogs
class TestGetDlrnApi(ConfigCases):

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    @patch('common.check_port')
    def test_get_dlrn_api_url_local(self, check_port_mock,
                                    mock_log_debug,
                                    mock_log_error):
        check_port_mock.return_value = True
        config = PromoterConfigFactory(self.filepaths['correct'], filters=[],
                                       validate=[])
        in_config = {}
        expected_url = "http://localhost:58080"
        api_url = config.get_dlrn_api_url(in_config)
        self.assertEqual(api_url, expected_url)
        check_port_mock.assert_has_calls([
            mock.call("localhost", "58080")
        ])
        mock_log_debug.assert_has_calls([
            mock.call("Assigning api_url %s", expected_url)
        ])
        mock_log_error.assert_not_called()

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    @patch('common.check_port')
    def test_get_dlrn_api_url_none(self, check_port_mock,
                                   mock_log_debug,
                                   mock_log_error):
        check_port_mock.side_effect = [False, False]
        config = PromoterConfigFactory(self.filepaths['correct'], filters=[],
                                       validate=[])
        # PromoterConfig calls log.debug at this point, so we reset the mock
        # to make it count from zero
        mock_log_debug.reset_mock()
        in_config = {
            'distro_name': "centos",
            'distro_version': "8",
            'release': "master"
        }
        expected_url = None
        api_url = config.get_dlrn_api_url(in_config)
        self.assertEqual(api_url, expected_url)
        check_port_mock.assert_has_calls([
            mock.call("localhost", "58080"),
            mock.call("trunk.rdoproject.org", 443, 5)
        ])
        mock_log_error.assert_has_calls([
            mock.call("No valid API url found")
        ])
        mock_log_debug.assert_not_called()

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    @patch('common.check_port')
    def test_get_dlrn_api_url_remote_centos8_master(self, check_port_mock,
                                                    mock_log_debug,
                                                    mock_log_error):
        check_port_mock.side_effect = [False, True]
        config = PromoterConfigFactory(self.filepaths['correct'], filters=[],
                                       validate=[])
        in_config = {
            'distro_name': "centos",
            'distro_version': "8",
            'release': "master"
        }
        expected_url = "https://trunk.rdoproject.org/api-centos8-master-uc"
        api_url = config.get_dlrn_api_url(in_config)
        self.assertEqual(api_url, expected_url)
        check_port_mock.assert_has_calls([
            mock.call("localhost", "58080"),
            mock.call("trunk.rdoproject.org", 443, 5)
        ])
        mock_log_debug.assert_has_calls([
            mock.call("Assigning api_url %s", expected_url)
        ])
        mock_log_error.assert_not_called()

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    @patch('common.check_port')
    def test_get_dlrn_api_url_remote_centos7_master(self, check_port_mock,
                                                    mock_log_debug,
                                                    mock_log_error):
        check_port_mock.side_effect = [False, True]
        config = PromoterConfigFactory(self.filepaths['correct'], filters=[],
                                       validate=[])
        in_config = {
            'distro_name': "centos",
            'distro_version': "7",
            'release': "master"
        }
        expected_url = "https://trunk.rdoproject.org/api-centos-master-uc"
        api_url = config.get_dlrn_api_url(in_config)
        self.assertEqual(api_url, expected_url)
        check_port_mock.assert_has_calls([
            mock.call("localhost", "58080"),
            mock.call("trunk.rdoproject.org", 443, 5)
        ])
        mock_log_debug.assert_has_calls([
            mock.call("Assigning api_url %s", expected_url)
        ])
        mock_log_error.assert_not_called()

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    @patch('common.check_port')
    def test_get_dlrn_api_url_remote_centos7_train(self, check_port_mock,
                                                   mock_log_debug,
                                                   mock_log_error):
        check_port_mock.side_effect = [False, True]
        config = PromoterConfigFactory(self.filepaths['correct'], filters=[],
                                       validate=[])
        in_config = {
            'distro_name': "centos",
            'distro_version': "7",
            'release': "train"
        }
        expected_url = "https://trunk.rdoproject.org/api-centos-train"
        api_url = config.get_dlrn_api_url(in_config)
        self.assertEqual(api_url, expected_url)
        check_port_mock.assert_has_calls([
            mock.call("localhost", "58080"),
            mock.call("trunk.rdoproject.org", 443, 5)
        ])
        mock_log_debug.assert_has_calls([
            mock.call("Assigning api_url %s", expected_url)
        ])
        mock_log_error.assert_not_called()


class TestExpandConfig(ConfigCases):

    @patch('config.PromoterConfig.get_dlrn_api_url')
    def test_expand_config_all_defaults(self, get_api_url_mock):
        self.maxDiff = None
        # All fields already present

        api_url = "http://localhost:58080"
        expected_config = {
            'allowed_clients':
                ['registries_client', 'qcow_client', 'dlrn_client'],
            'api_url': api_url,
            'containers_list_base_url':
                'https://opendev.org/openstack/tripleo-common/raw/commit/',
            'containers_list_path':
                'container-images/overcloud_containers.yaml.j2',
            'distro': 'centos7',
            'distro_name': 'centos',
            'distro_version': '7',
            'dlrnauth_password': None,
            'dlrnauth_username': 'ciuser',
            'dry_run': False,
            'latest_hashes_count': 10,
            'log_file': mock.ANY,
            'log_level': 20,
            'manifest_push': False,
            'promotion_criteria_map': {},
            'release': 'master',
            'repo_url': 'https://trunk.rdoproject.org/centos7-master',
            'target_registries_push': True
        }

        in_config = {
            'promotions': {}
        }
        get_api_url_mock.return_value = api_url
        config = PromoterConfigFactory(self.filepaths['correct'], filters=[],
                                       validate=None)
        out_config = config.expand_config(in_config)
        self.assertEqual(out_config, expected_config)

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_expand_config_complete(self):
        # All optional fields missing
        assert False
