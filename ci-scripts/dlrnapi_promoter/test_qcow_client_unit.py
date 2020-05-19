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
    FileExistsError = OSError

from promoter_integration_checks import check_links

from common import PromotionError
from dlrn_hash import DlrnHash
from test_unit_fixtures import ConfigSetup, hashes_test_cases


class TestQcowConnectionClient(unittest.TestCase):
    pass


class TestQcowClientPromotion(ConfigSetup):

    def setUp(self):
        super(TestQcowClientPromotion, self).setUp()
        self.client = self.promoter.qcow_client

        self.images_root = self.client.root
        self.images_dir = self.client.images_dir
        self.previous_hash_dir = os.path.join(self.images_dir, "efgh")
        self.current_hash_dir = os.path.join(self.images_dir, "dunno")
        self.candidate_hash_dir = os.path.join(self.images_dir, "abcd")
        self.target_label = "test-label"
        self.previous_target_label = "previous-{}".format(self.target_label)

        try:
            os.makedirs(self.candidate_hash_dir)
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

    def tearDown(self):
        super(TestQcowClientPromotion, self).tearDown()
        os.chdir("/")
        shutil.rmtree(self.images_root)

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    def test_promote_success_no_previous(self,
                                         mock_log_info,
                                         mock_log_error):

        self.client.promote(self.valid_candidate_hash, self.target_label,
                            create_previous=False)

        promotion_link = os.path.join(self.images_dir, self.target_label)
        check_links(os, promotion_link, "test", os.path.basename(self.candidate_hash_dir))

        self.assertFalse(mock_log_error.called)

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    def test_promote_success_previous(self,
                                      mock_log_info,
                                      mock_log_error):

        os.symlink(self.previous_hash_dir, os.path.join(self.images_dir,
                                                        self.target_label))
        os.symlink(self.previous_hash_dir,
                   os.path.join(self.images_dir, self.previous_target_label))

        self.client.promote(self.valid_candidate_hash, self.target_label)

        promotion_link = os.path.join(self.images_dir, "test")
        previous_link = os.path.join(self.images_dir, "previous-test")
        previous_dir = os.path.join(self.images_dir, "efgh")
        check_links(os, promotion_link, "test", os.path.basename(
            self.candidate_hash_dir), previous_link=previous_link,
                    previous_dir=previous_dir)

        self.assertFalse(mock_log_error.called)

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    def test_promote_failure_missing_candidate_dir(self,
                                                   mock_log_info,
                                                   mock_log_error):
        with self.assertRaises(PromotionError):
            self.client.promote(self.missing_candidate_hash, self.target_label)
        self.assertTrue(mock_log_error.called)


class TestQowClientValidation(ConfigSetup):
    pass

