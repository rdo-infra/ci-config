import os
import shutil
import tempfile
import unittest

import yaml

try:
    # Python3 imports
    import unittest.mock as mock
    from unittest.mock import patch
except ImportError:
    # Python2 imports
    from mock import patch
    import mock

from argparse import Namespace
from collections import OrderedDict

from promoter.common import close_logging, get_log_file, setup_logging
from promoter.config import (ConfigCore, ConfigError, PromoterConfig,
                             PromoterConfigFactory)

if not hasattr(__builtins__, "basestring"):
    basestring = (str, bytes)


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
                                          "-recursivelyrendered"),
            'empty_string': '',
        }
        self.config = ConfigCore(['high_priority', 'low_priority', None,
                                  'null_layer'])
        self.config._verbose = True
        self.config._layers['high_priority'] = high_priority_settings
        self.config._layers['low_priority'] = low_priority_settings
        self.config._layers['null_layer'] = None

        class SubConfig(ConfigCore):

            def _constructor_constructed(self):
                return "constructed-value"

            def _filter_filtered(self, value):
                return value.lower()

        self.subconfig = SubConfig(['layer'])
        self.subconfig._verbose = True
        self.subconfig._layers['layer'] = {'filtered': 'VALUE'}

    @patch('logging.Logger.warning')
    def test_get_unknown_attribute_skip_null(self, mock_log_warning):
        with self.assertRaises(AttributeError):
            _ = self.config.nonexsting_setting
        # Check also we are skipping search on null layer
        self.assertTrue(mock_log_warning.called)

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

    def test_render_empty_string(self):
        # it should render empty strings a empty strings, not None
        self.assertEqual(self.config.empty_string, '')

    def test_item_assignement(self):
        self.config['item_key'] = 'item_value'
        self.assertEqual(self.config['item_key'], 'item_value')


class ConfigTestCases(unittest.TestCase):

    def setUp(self):
        setup_logging("promoter", 10)
        self.upstream_defaults = {
            'release': 'master',
            'distro_name': 'centos',
            'distro_version': '7',
            'dlrnauth_username': 'ciuser',
            'manifest_push': "false",
            'target_registries_push': "true",
            'latest_hashes_count': 10,
            'log_level': "INFO",
            "dlrn_api_host": "trunk.rdoproject.org",
            "containers_list_base_url": ("https://opendev.org/openstack/"
                                         "tripleo-common/raw/commit/"),
            "containers_list_path":
                "container-images/overcloud_containers.yaml.j2",
            "repo_url": "https://{{ dlrn_api_host }}/{{ distro }}-{{ release "
                        "}}",
            'log_file': "/dev/null",
        }
        self.downstream_defaults = {
            'release': 'rhos-17',
            'distro_name': 'centos',
            'distro_version': '7',
            'dlrnauth_username': 'ciuser',
            'manifest_push': "false",
            'target_registries_push': "true",
            'latest_hashes_count': 10,
            'log_level': "INFO",
            "dlrn_api_host": "trunk.rdoproject.org",
            "containers_list_base_url": ("https://opendev.org/openstack/"
                                         "tripleo-common/raw/commit/"),
            "containers_list_path":
                "container-images/overcloud_containers.yaml.j2",
            "repo_url": "https://{{ dlrn_api_host }}/{{ distro }}-{{ release "
                        "}}",
            'log_file': "/dev/null",
        }
        self.null_settings = {
            'dlrn_api_host': None,
            'dlrn_api_port': None,
            'dlrn_api_scheme': None,
            'release': None,
            'distro_name': None,
            'distro_version': None,
            'allowed_clients': None,
            'promotions': None,
        }
        self.release_settings_master = {
            'dlrn_api_host': 'trunk.rdoproject.org',
            'dlrn_api_scheme': 'https',
            'dlrn_api_port': 443,
            'release': 'master',
            'distro_version': "8",
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
        self.release_missing_promotion_info = {
            'promotions': {
                'target-label': {
                }
            }
        }
        self.release_settings_invalid_logging = {
            'log_file': "/no/no/this/does/not/exist",
            'log_level': "CATACLYSM"
        }
        self.release_settings_empty_criteria = {
            'dlrn_api_host': 'localhost',
            'dlrn_api_port': None,
            'dlrn_api_scheme': 'http',
            'release': 'stablebranch',
            'distro_name': 'CeNtOs',
            'distro_version': "7",
            'allowed_clients': "dlrn_client,registries_client,qcow_client",
            'promotions': {
                'target-label': {
                    'candidate_label': 'candidate-label',
                    'criteria': []
                }
            },
        }
        self.release_settings_stablebranch = {
            'dlrn_api_host': 'localhost',
            'dlrn_api_port': None,
            'dlrn_api_scheme': 'http',
            'release': 'stablebranch',
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
        self.cli_settings = {
            'dlrn_api_host': 'trunk.rdoproject.org',
            'dlrn_api_scheme': 'https',
            'dlrn_api_port': 443,
            'release': 'master',
            'distro_version': "8",
            'default_qcow_server': 'localhost'
        }


class TestPromoterConfig(ConfigTestCases):

    def setUp(self):
        super(TestPromoterConfig, self).setUp()
        self.config_empty = PromoterConfig(global_defaults=self.null_settings)
        self.config_empty._verbose = True
        self.config_stablebranch = \
            PromoterConfig(environment_defaults=self.upstream_defaults,
                           release_settings=self.release_settings_stablebranch)
        self.config_stablebranch._verbose = True
        self.config_master = \
            PromoterConfig(environment_defaults=self.downstream_defaults,
                           release_settings=self.release_settings_master,
                           cli_settings=self.cli_settings)
        self.config_master._verbose = True
        self.config_incomplete = \
            PromoterConfig(environment_defaults=self.downstream_defaults,
                           release_settings=self.release_missing_promotion_info)
        self.config_incomplete._verbose = True

    def test_base_instance(self):
        config = PromoterConfig()
        config._verbose = True
        assert hasattr(config, "_layers")
        self.assertIsInstance(config._layers, OrderedDict)
        for layer_name in ['cli', 'release', 'extra', 'environment_defaults',
                           'global_defaults']:
            self.assertIn(layer_name, config._layers)
            self.assertIsInstance(config._layers[layer_name], dict)

    def test_constructor_dlrnauth_password_present(self):
        os.environ["DLRNAPI_PASSWORD"] = "test"
        self.assertEqual(self.config_empty.dlrnauth_password, "test")
        del (os.environ['DLRNAPI_PASSWORD'])

    def test_constructor_dlrnauth_password_absent(self):
        try:
            del (os.environ['DLRNAPI_PASSWORD'])
        except KeyError:
            pass
        self.assertIsNone(self.config_empty.dlrnauth_password)

    def test_constructor_qcow_server_default(self):
        server_info = self.config_master.qcow_server
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
        self.assertListEqual(self.config_stablebranch.allowed_clients,
                             expected_list)

    def test_filter_allowed_clients_notstring(self):
        self.assertIsNone(self.config_empty.allowed_clients)

    def test_filter_distro_name_string(self):
        self.assertTrue(self.config_stablebranch['distro_name'], "centos")

    def test_filter_distro_name_notstring(self):
        self.assertIsNone(self.config_empty['distro_name'])

    def test_filter_promotions_notdict(self):
        self.assertIsNone(self.config_empty.promotions)

    @patch('logging.Logger.debug')
    def test_filter_promotions_no_criteria(self, mock_log_debug):
        promotions = self.config_incomplete.promotions
        for __, info in promotions.items():
            self.assertNotIn('criteria', info)
        mock_log_debug.assert_has_calls([
            mock.call("No criteria info")
        ])

    def test_filter_promotions_dict(self):
        promotions = self.config_stablebranch.promotions
        for __, info in promotions.items():
            self.assertIsInstance(info['criteria'], set)

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    def test_get_dlrn_api_url_stablebranch(self,
                                           mock_log_debug,
                                           mock_log_error):
        expected_url = "http://localhost/api-centos-stablebranch"
        api_url = self.config_stablebranch.api_url
        self.assertEqual(api_url, expected_url)
        mock_log_debug.assert_has_calls([
            mock.call("Assigning api_url %s", expected_url)
        ])

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
    def test_get_dlrn_api_url_master(self,
                                     mock_log_debug,
                                     mock_log_error):
        expected_url = "https://trunk.rdoproject.org/api-centos8-master-uc"
        api_url = self.config_master.api_url
        self.assertEqual(api_url, expected_url)
        mock_log_debug.assert_has_calls([
            mock.call("Assigning api_url %s", expected_url)
        ])

    def test_constructor_namespace_ussuri(self):
        self.config_stablebranch.release = "ussuri"
        self.assertEqual(self.config_stablebranch.source_namespace, "tripleou")
        self.assertEqual(self.config_stablebranch.target_namespace, "tripleou")

    def test_constructor_namespace_notussuri(self):
        self.assertEqual(self.config_master.source_namespace, "tripleomaster")
        self.assertEqual(self.config_master.target_namespace, "tripleomaster")


class TestPromoterConfigFactory(ConfigTestCases):
    """
    Config Tree
    script_root
    `- config_environments
       |- global_defaults.yaml
       `- environment_root
          |- defaults.yaml
          |- custom.py
          `- CentOS-8
             `- release.yaml
    """

    def setUp(self):
        super(TestPromoterConfigFactory, self).setUp()
        self.default_settings = {
            'invalid': "",
            'empty': "",
            'null': {},
            'missing': {},
            'invalid_logging': self.upstream_defaults,
            'empty_criteria': self.upstream_defaults,
            'missing_promotion_info': self.upstream_defaults,
            'upstream': self.upstream_defaults,
            'downstream': self.downstream_defaults,
        }
        self.release_settings = {
            'invalid': "",
            'empty': "",
            'null': self.null_settings,
            'missing': {},
            'invalid_logging': self.release_settings_invalid_logging,
            'empty_criteria': self.release_settings_empty_criteria,
            'missing_promotion_info': self.release_missing_promotion_info,
            'upstream': self.release_settings_stablebranch,
            'downstream': self.release_settings_master,
        }
        self.env_paths = {}

        for env_name in self.default_settings:
            temp_dir_name = "config-test-{}-".format(env_name)
            temp_dir = tempfile.mkdtemp(prefix=temp_dir_name)
            self.env_paths[env_name] = temp_dir
            defaults_path = os.path.join(temp_dir, "defaults.yaml")
            yaml_defaults = yaml.safe_dump(self.default_settings[env_name])
            with open(defaults_path, "w") as defaults_file:
                defaults_file.write(yaml_defaults)
            if env_name == 'invalid':
                with open(defaults_path, "w") as defaults_file:
                    defaults_file.write("[invalid yaml data]\nvery invalid")

            release_dir = os.path.join(temp_dir, "CentOS-8")
            os.mkdir(release_dir)
            release_settings_path = os.path.join(temp_dir, release_dir,
                                                 "release.yaml")
            yaml_release = yaml.safe_dump(self.release_settings[env_name])
            with open(release_settings_path, "w") as release_file:
                release_file.write(yaml_release)
        release_config = "CentOS-8/master.yaml"
        log_file = os.path.expanduser(get_log_file('staging',
                                                   release_config))
        log_dir = "/".join(log_file.split("/")[:-1])
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        self.config_builder = PromoterConfigFactory(**{'log_file': log_file})

    def tearDown(self):
        close_logging("promoter")
        for path in self.env_paths.values():
            shutil.rmtree(path)

    def test_cli_settings_namespace(self):
        """
        Ensure Namespace from cli gets transformed into dict
        """
        cli_args = Namespace()
        config = self.config_builder(self.env_paths['upstream'], None,
                                     cli_args=cli_args,
                                     validate=None)
        self.assertIsInstance(config._layers['cli'], dict)

    @patch('logging.Logger.error')
    def test_config_no_env_root(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(None, None)
        mock_log_error.assert_has_calls([
            mock.call("%s can't be empty", "Environment root")
        ])

    @patch('logging.Logger.error')
    def test_config_no_release_settings(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(self.env_paths['upstream'], None)
        mock_log_error.assert_has_calls([
            mock.call("%s can't be empty", "Path")
        ])

    @patch('logging.Logger.error')
    def test_config_not_found(self, mock_log_error):
        with self.assertRaises(OSError):
            self.config_builder(self.env_paths['upstream'], "/does/not/exist")
        mock_log_error.assert_has_calls([
            mock.call('%s %s not found', 'Path', '/does/not/exist')
        ])

    @patch('logging.Logger.error')
    def test_load_empty_insufficient_yaml_config(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(self.env_paths['empty'],
                                "CentOS-8/release.yaml")
        mock_log_error.assert_has_calls([
            mock.call("Config file %s does not contain valid data",
                      os.path.join(self.env_paths['empty'], "defaults.yaml"))
        ])

    @patch('logging.Logger.error')
    def test_load_invalid_yaml_config(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(self.env_paths['invalid'],
                                "CentOS-8/release.yaml")
        mock_log_error.assert_has_calls([
            mock.call("Not a valid yaml: %s",
                      os.path.join(self.env_paths['invalid'], "defaults.yaml"))
        ])

    @patch('logging.Logger.error')
    def test_load_yaml_file_missing_promotion_info(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(self.env_paths['missing_promotion_info'],
                                "CentOS-8/release.yaml",
                                validate="promotions")
        mock_log_error.assert_has_calls([
            mock.call('Validation Error: %s',
                      'Missing criteria for target target-label, '
                      'Missing candidate label for target target-label'),
            mock.call("Error in configuration")
        ])

    @patch('logging.Logger.error')
    def test_load_yaml_file_invalid_log_options(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(self.env_paths['invalid_logging'],
                                "CentOS-8/release.yaml",
                                validate="logs")
        mock_log_error.assert_has_calls([
            mock.call('Validation Error: %s',
                      'Invalid log file /no/no/this/does/not/exist,'
                      ' Unrecognized log level: CATACLYSM'),
            mock.call('Error in configuration')
        ])

    @patch('logging.Logger.error')
    def test_load_yaml_file_empty_criteria(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(self.env_paths['empty_criteria'],
                                "CentOS-8/release.yaml",
                                validate="promotions")
        mock_log_error.assert_has_calls([
            mock.call('Validation Error: %s', 'Empty criteria for target '
                                              'target-label'),
            mock.call("Error in configuration")
        ])

    @patch('logging.Logger.error')
    def test_load_config_missing_promotions(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(self.env_paths['missing'],
                                "CentOS-8/release.yaml",
                                validate="promotions")
        mock_log_error.assert_has_calls([
            mock.call('Validation Error: %s', 'Missing promotions section'),
            mock.call("Error in configuration")
        ])

    @patch('logging.Logger.error')
    def test_load_config_empty_promotions(self, mock_log_error):
        with self.assertRaises(ConfigError):
            self.config_builder(self.env_paths['null'],
                                "CentOS-8/release.yaml",
                                validate="promotions")
        mock_log_error.assert_has_calls([
            mock.call('Validation Error: %s', 'Empty promotions section'),
            mock.call("Error in configuration")
        ])

    @patch('logging.Logger.error')
    def test_load_config_missing_pass(self, mock_log_error):
        try:
            del (os.environ["DLRNAPI_PASSWORD"])
        except KeyError:
            pass
        with self.assertRaises(ConfigError):
            self.config_builder(self.env_paths['null'],
                                "CentOS-8/release.yaml",
                                validate="password")
        mock_log_error.assert_has_calls([
            mock.call('Validation Error: %s',
                      'No dlrnapi password found in env'),
            mock.call("Error in configuration")
        ])

    def test_load_correct_yaml_file_verify_params(self):
        self.maxDiff = None
        # Test for load correctness
        os.environ["DLRNAPI_PASSWORD"] = "test"
        config = self.config_builder(self.env_paths['upstream'],
                                     "CentOS-8/release.yaml")
        # Test if config keys are there and have a value
        assert hasattr(config, "release"), "Missing mandatory argument"
        assert hasattr(config, "distro_name"), "Missing mandatory argument"
        self.assertIsInstance(config.distro_name, basestring)
        self.assertEqual(config.release, "stablebranch")
        self.assertEqual(config.latest_hashes_count, 10)
        # TODO(gcerami) we should also check that ~ in log_file are expanded
        #  to user home, but it's not easy as setting log_file to something
        #  different from /dev/null will need a valid file to write logs to,
        #  and it cannot be in the user home
