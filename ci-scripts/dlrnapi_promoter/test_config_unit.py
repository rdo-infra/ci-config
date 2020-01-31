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

from config import ConfigError, PromoterConfigBase, PromoterConfig
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
            PromoterConfigBase(None)

    @patch('logging.Logger.error')
    def test_config_not_found(self, mock_log_error):
        with self.assertRaises(OSError):
            PromoterConfigBase("/does/not/exist")
        mock_log_error.assert_has_calls([
            mock.call("Configuration file not found")
        ])

    def test_load_notini_config(self):
        with self.assertRaises(ConfigError):
            PromoterConfigBase(self.filepaths['not_ini'])

    @patch('logging.Logger.error')
    def test_load_ini_file_no_criteria(self, mock_log_error):
        with self.assertRaises(ConfigError):
            PromoterConfigBase(self.filepaths['missing_criteria_section'])
        mock_log_error.assert_has_calls([
            mock.call("Missing criteria section for target %s",
                      'current-tripleo')
        ])

    @patch('logging.Logger.error')
    def test_load_config_missing_main(self, mock_log_error):
        with self.assertRaises(ConfigError):
            PromoterConfigBase(self.filepaths['missing_main'])
        mock_log_error.assert_has_calls([
            mock.call("Config file: %s Missing main section",
                      self.filepaths['missing_main'])
        ])

    @patch('logging.Logger.error')
    def test_load_config_missing_promotions(self, mock_log_error):
        with self.assertRaises(ConfigError):
            PromoterConfigBase(self.filepaths['missing_promotions_section'])
        mock_log_error.assert_has_calls([
            mock.call("Missing promotion_from section")
        ])

    def test_load_correct_ini_file_verify_params(self):
        self.maxDiff = None
        # Test for load correctness
        os.environ["DLRNAPI_PASSWORD"] = "test"
        config = PromoterConfigBase(self.filepaths['correct'])
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
        config = PromoterConfig(self.filepaths['correct'])
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
        PromoterConfig(ini_config)
        calls = [
            mock.call('Missing parameter in configuration file: %s. Using '
                      'default value: %s', 'distro_name', 'centos')
        ]
        mock_warning.assert_has_calls(calls)
        self.assertFalse(mock_error.called)

    @patch('logging.Logger.error')
    def test_load_ini_file_no_pass(self, mock_error):
        try:
            del(os.environ["DLRNAPI_PASSWORD"])
        except KeyError:
            pass
        with self.assertRaises(ConfigError):
            PromoterConfig(self.filepaths['correct'])
        calls = [
            mock.call('No dlrnapi password found in env'),
        ]
        mock_error.assert_has_calls(calls, any_order=True)

    @patch('logging.Logger.error')
    def test_load_empty_criteria(self, mock_error):
        os.environ["DLRNAPI_PASSWORD"] = "test"
        with self.assertRaises(ConfigError):
            PromoterConfig(self.filepaths['criteria_empty'])
        calls = [
            mock.call('No jobs in criteria for target %s', 'current-tripleo'),
            mock.call('Error in configuration file {}'
                      ''.format(self.filepaths['criteria_empty']))
        ]
        mock_error.assert_has_calls(calls, any_order=True)


class TestGetDlrnApi(ConfigBase):

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_get_dlrn_api_url_none(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_get_dlrn_api_url_local(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_get_dlrn_api_url_remote(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_experimental_config(self):
        assert False


class TestSanityChecks(ConfigBase):

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_sanity_check_all_checks(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_sanity_check_single_check(self):
        assert False


class TestExpandConfig(ConfigBase):

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_expand_config_complete(self):
        # All fields already present
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_expand_config_incomplete(self):
        # All optional fields missing
        assert False


class TestHandleOverrides(ConfigBase):

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_handle_overrides_overrides_exists_but_empty(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_handle_overrides_overrides_nonexisting(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_handle_overrides_ok(self):
        assert False
