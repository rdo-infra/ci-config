import pytest
import os
import shutil
import stat

try:
    # Python3 imports
    from unittest.mock import Mock, patch
    import unittest.mock as mock
except ImportError:
    # Python2 imports
    from mock import Mock, patch
    import mock

try:
    FileExistsError
except NameError:
    FileExistsError = IOError

from promoter_integration_checks import check_links

from common import PromotionError
from dlrn_hash import DlrnHash
from test_unit_fixtures import ConfigSetup, hashes_test_cases


class TestQcowClient(ConfigSetup):

    def setUp(self):
        super(TestQcowClient, self).setUp()
        self.client = self.promoter.qcow_client

        self.images_root = self.client.root
        self.images_dir = self.client.images_dir
        self.hash_dir = os.path.join(self.images_dir, "abcd")
        self.previous_hash_dir = os.path.join(self.images_dir, "efgh")
        try:
            os.makedirs(self.hash_dir)
        except FileExistsError:
            pass
        try:
            os.makedirs(self.previous_hash_dir)
        except FileExistsError:
            pass

        self.valid_candidate_hash = \
            DlrnHash(source=hashes_test_cases['aggregate']['dict']['valid'])
        self.missing_candidate_hash = \
            DlrnHash(source=hashes_test_cases['aggregate']['dict']['different'])
        self.target_label = "test"

    def tearDown(self):
        super(TestQcowClient, self).tearDown()
        os.chdir("/")
        shutil.rmtree(self.images_root)

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    def test_promote_success_no_previous(self,
                             mock_log_info,
                             mock_log_error
                             ):

        self.client.promote(self.valid_candidate_hash, self.target_label)

        promotion_link = os.path.join(self.images_dir, self.target_label)
        check_links(os, promotion_link, "test", os.path.basename(self.hash_dir))

        self.assertFalse(mock_log_error.called)

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    def test_promote_success_previous(self,
                             mock_log_info,
                             mock_log_error
                             ):

        self.client.promote(self.valid_candidate_hash, self.target_label)

        promotion_link = os.path.join(self.images_dir, "test")
        previous_link = os.path.join(self.images_dir, "previous-test")
        check_links(os, promotion_link, "test", os.path.basename(self.hash_dir))

        self.assertFalse(mock_log_error.called)

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    def test_promote_failure_missing_candidate_dir(self,
                             mock_log_info,
                             mock_log_error):
        with self.assertRaises(PromotionError):
            self.client.promote(self.missing_candidate_hash, self.target_label)
        self.assertTrue(mock_log_error.called)

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    def test_promote_failure_linking(self,
                                     mock_log_info,
                                     mock_log_error):
        with self.assertRaises(PromotionError):
            self.client.promote(self.missing_candidate_hash, self.target_label)
        self.assertTrue(mock_log_error.called)
