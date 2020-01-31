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

from config import ConfigError, PromoterConfig
from test_promoter_common_unit import test_ini_configurations


class TestConfigBase(unittest.TestCase):

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

    def test_load_notini_config(self):
        with self.assertRaises(ConfigError):
            PromoterConfig(self.filepaths['not_ini'])

    # FIXME: python2 has no unittest.assertLogs
    @patch('logging.Logger.warning')
    @patch('logging.Logger.error')
    def test_load_defective_ini_file(self, mock_error, mock_warning):
        os.environ["DLRNAPI_PASSWORD"] = "test"
        ini_config = self.filepaths['missing_parameters']
        with self.assertRaises(ConfigError):
            PromoterConfig(ini_config)
        calls = [
            mock.call('Missing parameter in configuration file: '
                      'distro_name.Using default value: centos')
        ]
        mock_warning.assert_has_calls(calls)
        calls = [
            mock.call('Invalid Log file: /dev/nul'),
            mock.call('Error in configuration file %s' % str(ini_config))
        ]
        mock_error.assert_has_calls(calls, any_order=True)

    def test_load_ini_file_no_criteria(self):
        with self.assertRaises(ConfigError):
            PromoterConfig(self.filepaths['missing_section'])

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

    def test_load_correct_ini_file_verify_params(self):
        self.maxDiff = None
        # Test for load correctness
        os.environ["DLRNAPI_PASSWORD"] = "test"
        config = PromoterConfig(self.filepaths['correct'])
        # Test if config keys are there and have a value
        assert hasattr(config, "release"), "Missing mandatory argument"
        assert hasattr(config, "distro_name"), "Missing mandatory argument"
        self.assertIsInstance(config.distro_name, string_types)
        self.assertEqual(config.release, "master")
        self.assertEqual(config.target_registries_push, True)
        promotion_criteria_map = {
            "current-tripleo": {
                "periodic-tripleo-centos-7-master-containers-build-push"
            }
        }
        self.assertDictEqual(promotion_criteria_map,
                             config.promotion_criteria_map)
        self.assertEqual(config.latest_hashes_count, 10)

    @pytest.mark.xfail(reason="Not implemented")
    def test_config_missing_file(self):
        assert False


class TestConfig(unittest.TestCase):

    def setUP(self):
        """
        Create Promoter config instance ?
        :return:
        """
        pass

    @pytest.mark.xfail(reason="Not implemented")
    def test_get_dlrn_api_url_none(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_get_dlrn_api_url_local(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_get_dlrn_api_url_remote(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_experimental_config(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_sanity_check(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_get_expand_config(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_handle_overrides(self):
        assert False
