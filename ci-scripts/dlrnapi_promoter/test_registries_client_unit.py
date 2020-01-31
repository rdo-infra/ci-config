import pytest
import subprocess
try:
    # Python3 imports
    from unittest.mock import Mock, patch
    import unittest.mock as mock
except ImportError:
    # Python2 imports
    from mock import Mock, patch
    import mock

from common import PromotionError
from dlrn_hash import DlrnHash
from test_unit_fixtures import ConfigSetup, hashes_test_cases


class TestRegistriesClient(ConfigSetup):

    def setUp(self):
        super(TestRegistriesClient, self).setUp()
        self.client = self.promoter.registries_client

    def test_setup(self):
        error_msg = "Container push logfile is misplaced"
        assert self.client.logfile != "", error_msg

    @pytest.mark.xfail(reason="not implemented", run=False)
    def test_prepare_extra_vars_missing_reader(self):
        assert False

    @pytest.mark.xfail(reason="not implemented", run=False)
    def test_prepare_extra_vars_missing_sha(self):
        assert False

    @pytest.mark.xfail(reason="not implemented", run=False)
    def test_prepare_extra_vars_empty_list(self):
        assert False

    @pytest.mark.xfail(reason="not implemented", run=False)
    def test_prepare_extra_vars_success(self):
        assert False

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('os.unlink')
    @patch('registries_client.RegistriesClient.prepare_extra_vars')
    @mock.patch('subprocess.check_output')
    def test_promote_success(self, check_output_mock,
                             extra_vars_mock,
                             unlink_mock,
                             mock_log_info,
                             mock_log_error
                             ):
        candidate_hash =\
            DlrnHash(source=hashes_test_cases['aggregate']['dict']['valid'])
        target_label = "test"

        check_output_mock.return_value = "test log"
        self.client.promote(candidate_hash, target_label)

        self.assertTrue(check_output_mock.called)
        self.assertFalse(mock_log_error.called)

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('os.unlink')
    @patch('registries_client.RegistriesClient.prepare_extra_vars')
    @mock.patch('subprocess.check_output')
    def test_promote_failure(self, check_output_mock,
                             extra_vars_mock,
                             unlink_mock,
                             mock_log_info,
                             mock_log_error
                             ):
        candidate_hash = \
            DlrnHash(source=hashes_test_cases['aggregate']['dict']['valid'])
        target_label = "test"
        exception = subprocess.CalledProcessError(1, 2)
        exception.output = b"test"
        check_output_mock.side_effect = exception
        with self.assertRaises(PromotionError):
            self.client.promote(candidate_hash, target_label)
        self.assertTrue(mock_log_error.called)
