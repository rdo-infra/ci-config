import os
import tempfile
import unittest

try:
    # Python3 imports
    from unittest import mock
    from unittest.mock import patch
except ImportError:
    # Python2 imports
    from mock import patch
    import mock

import pytest
from config_legacy import (ConfigError, PromoterLegacyConfig,
                           PromoterLegacyConfigBase)
from six import string_types
from test_unit_fixtures import test_ini_configurations


class ConfigBase(unittest.TestCase):

    def setUp(self):
        self.filepaths = {}
        for case, content in test_ini_configurations.items():
            fp, filepath = tempfile.mkstemp(prefix="ini_conf_test")
            with os.fdopen(fp, "w") as test_file:
                test_file.write(content)
            self.filepaths[case] = filepath

    def tearDown(self):
        for filepath in self.filepaths.values():
            os.unlink(filepath)


# Config in general is difficult to test singularly, as the init already calls
# all the  methods involved. Maybe we can add an option to defer calling other
# methods. but for now the best way is to just verify the final artifact
class TestConfigBase(ConfigBase):

    def test_config_none(self):
        with self.assertRaises(ConfigError):
            PromoterLegacyConfigBase(None)

    @patch('logging.Logger.error')
    def test_config_not_found(self, mock_log_error):
        with self.assertRaises(OSError):
            PromoterLegacyConfigBase("/does/not/exist")
        mock_log_error.assert_has_calls([
            mock.call("Configuration file not found")
        ])

    def test_load_notini_config(self):
        with self.assertRaises(ConfigError):
            PromoterLegacyConfigBase(self.filepaths['not_ini'])

    @patch('logging.Logger.error')
    def test_load_ini_file_no_criteria(self, mock_log_error):
        with self.assertRaises(ConfigError):
            PromoterLegacyConfigBase(self.filepaths['missing_criteria_section'])
        mock_log_error.assert_has_calls([
            mock.call("Missing criteria section for target %s",
                      'current-tripleo')
        ])

    @patch('logging.Logger.error')
    def test_load_config_missing_main(self, mock_log_error):
        with self.assertRaises(ConfigError):
            PromoterLegacyConfigBase(self.filepaths['missing_main'])
        mock_log_error.assert_has_calls([
            mock.call("Config file: %s Missing main section",
                      self.filepaths['missing_main'])
        ])

    @patch('logging.Logger.error')
    def test_load_config_missing_promotions(self, mock_log_error):
        with self.assertRaises(ConfigError):
            PromoterLegacyConfigBase(
                self.filepaths['missing_promotions_section'])
        mock_log_error.assert_has_calls([
            mock.call("Missing promotion_from section")
        ])

    def test_load_correct_ini_file_verify_params(self):
        self.maxDiff = None
        # Test for load correctness
        os.environ["DLRNAPI_PASSWORD"] = "test"
        config = PromoterLegacyConfigBase(self.filepaths['correct'])
        # Test if config keys are there and have a value
        assert hasattr(config, "release"), "Missing mandatory argument"
        assert hasattr(config, "distro_name"), "Missing mandatory argument"
        self.assertIsInstance(config.distro_name, string_types)
        self.assertEqual(config.release, "master")
        # TODO(gcerami) we should also check that ~ in log_file are expanded
        #  to user home, but it's not easy as setting log_file to something
        #  different from /dev/null will need a valid file to write logs to,
        #  and it cannot be in the user home
        # This is tricky, here we verified that the code correctly loaded the
        # value, and value from ini is text. In PromoterConfig we verify if
        # this value has been correctly handled and converted to int
        self.assertEqual(config.latest_hashes_count, '10')


class TestConfig(ConfigBase):

    def test_load_correct_verify_extended_params(self):
        self.maxDiff = None
        # Test for load correctness
        os.environ["DLRNAPI_PASSWORD"] = "test"
        config = PromoterLegacyConfig(self.filepaths['correct'])
        self.assertEqual(config.target_registries_push, True)
        promotion_criteria_map = {
            "current-tripleo": {
                "periodic-tripleo-centos-7-master-containers-build-push",
                "periodic-tripleo-centos-7-master-standalone"
            }
        }
        self.assertDictEqual(promotion_criteria_map,
                             config.promotion_criteria_map)

        # This is tricky, here we verified that the code correctly
        # converted this value to int In PromoterConfigBase we verify if
        # this value has just been correctly loaded as str from ini config
        self.assertEqual(config.latest_hashes_count, 10)

    # FIXME: python2 has no unittest.assertLogs
    @patch('logging.Logger.warning')
    @patch('logging.Logger.error')
    def test_load_defective_ini_file(self, mock_error, mock_warning):
        os.environ["DLRNAPI_PASSWORD"] = "test"
        ini_config = self.filepaths['missing_parameters']
        with self.assertRaises(ConfigError):
            PromoterLegacyConfig(ini_config)
        calls = [
            mock.call('Missing parameter in configuration file: %s. Using '
                      'default value: %s', 'distro_name', 'centos')
        ]
        mock_warning.assert_has_calls(calls)
        calls = [
            mock.call('Invalid Log file: %s', '/dev/nul'),
            mock.call('Error in configuration file %s' % str(ini_config))
        ]
        mock_error.assert_has_calls(calls, any_order=True)

    @patch('logging.Logger.error')
    def test_load_ini_file_no_pass(self, mock_error):
        try:
            del(os.environ["DLRNAPI_PASSWORD"])
        except KeyError:
            pass
        with self.assertRaises(ConfigError):
            PromoterLegacyConfig(self.filepaths['correct'])
        calls = [
            mock.call('No dlrnapi password found in env'),
        ]
        mock_error.assert_has_calls(calls, any_order=True)

    @patch('logging.Logger.error')
    def test_load_empty_criteria(self, mock_error):
        os.environ["DLRNAPI_PASSWORD"] = "test"
        with self.assertRaises(ConfigError):
            PromoterLegacyConfig(self.filepaths['criteria_empty'])
        calls = [
            mock.call('No jobs in criteria for target %s', 'current-tripleo'),
            mock.call('Error in configuration file {}'
                      ''.format(self.filepaths['criteria_empty']))
        ]
        mock_error.assert_has_calls(calls, any_order=True)


class TestGetDlrnApi(ConfigBase):

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    @patch('common.check_port')
    def test_get_dlrn_api_url_local(self, check_port_mock,
                                    mock_log_debug,
                                    mock_log_error):
        check_port_mock.return_value = True
        config = PromoterLegacyConfig(self.filepaths['correct'], filters=[],
                                      checks=[])
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
        self.assertFalse(mock_log_error.called)

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    @patch('common.check_port')
    def test_get_dlrn_api_url_none(self, check_port_mock,
                                   mock_log_debug,
                                   mock_log_error):
        check_port_mock.side_effect = [False, False]
        config = PromoterLegacyConfig(self.filepaths['correct'], filters=[],
                                      checks=[])
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
        self.assertFalse(mock_log_debug.called)

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    @patch('common.check_port')
    def test_get_dlrn_api_url_remote_centos8_master(self, check_port_mock,
                                                    mock_log_debug,
                                                    mock_log_error):
        check_port_mock.side_effect = [False, True]
        config = PromoterLegacyConfig(self.filepaths['correct'], filters=[],
                                      checks=[])
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
        self.assertFalse(mock_log_error.called)

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    @patch('common.check_port')
    def test_get_dlrn_api_url_remote_centos7_master(self, check_port_mock,
                                                    mock_log_debug,
                                                    mock_log_error):
        check_port_mock.side_effect = [False, True]
        config = PromoterLegacyConfig(self.filepaths['correct'], filters=[],
                                      checks=[])
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
        self.assertFalse(mock_log_error.called)

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    @patch('common.check_port')
    def test_get_dlrn_api_url_remote_centos7_train(self, check_port_mock,
                                                   mock_log_debug,
                                                   mock_log_error):
        check_port_mock.side_effect = [False, True]
        config = PromoterLegacyConfig(self.filepaths['correct'], filters=[],
                                      checks=[])
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
        self.assertFalse(mock_log_error.called)


class TestSanityChecks(ConfigBase):

    @patch('logging.Logger.error')
    @patch('logging.Logger.warning')
    def test_sanity_check_all_checks_success_all_warnings(self,
                                                          mock_log_warning,
                                                          mock_log_error):
        pconfig = PromoterLegacyConfig(self.filepaths['correct'], filters=[],
                                       checks=[])
        config = {
            'distro_name': "default_distro",
            'distro_version': "default_version",
            'dlrnauth_username': 'ciuser',
            'dlrnauth_password': 'pass',
            'promotion_criteria_map': {
                'current-tripleo': ['job1', 'job2']
            },
            'log_level': "INFO",
            "log_file": "/dev/null"
        }
        file_config = {'main': {}}
        conf_ok = pconfig.sanity_check(config, file_config)
        self.assertTrue(conf_ok)
        mock_log_warning.assert_has_calls([
            mock.call('Missing parameter in configuration file: %s. '
                      'Using default value: %s', "distro_version",
                      "default_version"),
            mock.call('Missing parameter in configuration file: %s. '
                      'Using default value: %s', "log_file",
                      "/dev/null"),
            mock.call('Missing parameter in configuration file: %s. '
                      'Using default value: %s', "distro_name",
                      "default_distro"),
            mock.call('Missing parameter in configuration file: username. '
                      'Using default value: %s', "ciuser")
        ], any_order=True)
        self.assertFalse(mock_log_error.called)

    @patch('logging.Logger.error')
    @patch('logging.Logger.warning')
    def test_sanity_check_all_checks_fail_all_errors(self,
                                                     mock_log_warning,
                                                     mock_log_error):
        pconfig = PromoterLegacyConfig(self.filepaths['correct'], filters=[],
                                       checks=[])
        config = {
            'distro_name': "default_distro",
            'distro_version': "default_version",
            'dlrnauth_password': None,
            'dlrnauth_username': 'ciuser',
            'promotion_criteria_map': {
                'current-tripleo': []
            },
            'log_level': "INFO",
            "log_file": "/tmp/not/existing/file.log"
        }
        file_config = {'main': {}}
        conf_ok = pconfig.sanity_check(config, file_config)
        self.assertFalse(conf_ok)
        mock_log_error.assert_has_calls([
            mock.call('Invalid Log file: %s', '/tmp/not/existing/file.log'),
            mock.call('No dlrnapi password found in env'),
            mock.call('No jobs in criteria for target %s', 'current-tripleo')
        ])


class TestExpandConfig(ConfigBase):

    @patch('config_legacy.PromoterLegacyConfig.get_dlrn_api_url')
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
            "containers_list_exclude_config": (
                "https://opendev.org/openstack/"
                "tripleo-ci/raw/branch/master/roles/build-containers/vars"
                "/main.yaml"),
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
            'source_namespace': "tripleomaster",
            'target_namespace': "tripleomaster",
            'target_registries_push': True,
            'overcloud_images': {'qcow_servers': {'local': {}}},
            'default_qcow_server': 'local',
            'qcow_server': {},
        }

        in_config = {
            'promotion_criteria_map': {},
            'overcloud_images': {
                'qcow_servers': {
                    "local": {}
                }
            },
            'default_qcow_server': "local"
        }
        get_api_url_mock.return_value = api_url
        config = PromoterLegacyConfig(self.filepaths['correct'], filters=[],
                                      checks=[])
        out_config = config.expand_config(in_config)
        self.assertEqual(out_config, expected_config)

    @patch('config_legacy.PromoterLegacyConfig.get_dlrn_api_url')
    def test_expand_config_ussuri(self, get_api_url_mock):
        api_url = "http://localhost:58080"
        in_config = {
            'promotion_criteria_map': {},
            'release': "ussuri",
            'overcloud_images': {
                'qcow_servers': {
                    'default_server': {}
                }
            },
            'default_qcow_server': 'default_server'
        }
        get_api_url_mock.return_value = api_url
        config = PromoterLegacyConfig(self.filepaths['correct'], filters=[],
                                      checks=[])
        out_config = config.expand_config(in_config)
        self.assertEqual(out_config['source_namespace'], "tripleou")
        self.assertEqual(out_config['target_namespace'], "tripleou")

    @patch('config_legacy.PromoterLegacyConfig.get_dlrn_api_url')
    def test_expand_config_namespace(self, get_api_url_mock):
        api_url = "http://localhost:58080"
        in_config = {
            'promotion_criteria_map': {},
            'source_namespace': "mysourcenamespace",
            'target_namespace': "mytargetnamespace",
            'overcloud_images': {
                'qcow_servers': {
                    'default_server': {}
                }
            },
            'default_qcow_server': 'default_server'
        }
        get_api_url_mock.return_value = api_url
        config = PromoterLegacyConfig(self.filepaths['correct'], filters=[],
                                      checks=[])
        out_config = config.expand_config(in_config)
        self.assertEqual(out_config['source_namespace'], "mysourcenamespace")
        self.assertEqual(out_config['target_namespace'], "mytargetnamespace")

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_expand_config_complete(self):
        # All optional fields missing
        assert False


class TestHandleOverrides(ConfigBase):

    def test_handle_overrides_no_overrides(self):
        overrides = type("Overrides", (), {})
        in_config = {
            'log_file': "/another/path/to/logs",
            'username': "foo",
            'log_level': "INFO"
        }
        config = PromoterLegacyConfig(self.filepaths['correct'], filters=[],
                                      checks=[])
        out_config = config.handle_overrides(in_config,
                                             overrides=overrides)
        self.assertEqual(out_config, in_config)

    @patch('logging.Logger.debug')
    def test_handle_overrides_some_overrides(self, mock_log_debug):
        overrides = type("Overrides", (), {
            'log_file': "/path/to/logs",
            'api_url': "http://api.url:8080"
        })
        in_config = {
            'log_file': "/another/path/to/logs",
            'api_url': "https://localhost:389"
        }
        config = PromoterLegacyConfig(self.filepaths['correct'], filters=[],
                                      checks=[])
        out_config = config.handle_overrides(in_config,
                                             overrides=overrides)
        self.assertEqual(out_config['log_file'], "/path/to/logs")
        self.assertEqual(out_config['api_url'], "http://api.url:8080")
        mock_log_debug.assert_has_calls([
            mock.call("Main config key %s not overridden", mock.ANY)
        ])
