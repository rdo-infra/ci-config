import os
import shutil
import tempfile
import unittest

import pytest
from promoter.common import PromotionError, get_log_file
from promoter.config import PromoterConfigFactory
from promoter.dlrn_hash import DlrnHash
from promoter.qcow_client import QcowConnectionClient

from .promoter_integration_checks import check_links
from .test_unit_fixtures import SSH_CONTENT, ConfigSetup, hashes_test_cases

try:
    # Python3 imports
    from unittest import mock
    from unittest.mock import patch
except ImportError:
    # Python2 imports
    import mock
    from mock import patch

try:
    FileExistsError
except NameError:
    FileExistsError = OSError


class TestQcowConnectionClient(unittest.TestCase):

    def setUp(self):
        fd, self.path = tempfile.mkstemp()
        ssh_file = os.fdopen(fd, "w")
        ssh_file.write(SSH_CONTENT)
        ssh_file.close()

        self.server_conf_os = {
            'client': 'os',
            'host': 'localhost',
            'user': os.environ['USER'],
            'keypath': self.path,
        }
        self.server_conf_sftp = {
            'host': 'localhost',
            'user': os.environ['USER'],
            'client': 'sftp',
            'keypath': self.path,
        }

    @patch('paramiko.SSHClient.close')
    @patch('paramiko.SSHClient.connect')
    def test_instance_os_connect_close(self, paramiko_connect_mock,
                                       paramiko_close_mock):
        client = QcowConnectionClient(self.server_conf_os)
        self.assertIsNotNone(client.getcwd())

        client.connect()
        self.assertFalse(paramiko_connect_mock.called)

        client.close()
        self.assertFalse(paramiko_close_mock.called)

    @patch('paramiko.SSHClient.close')
    @patch('paramiko.SSHClient.connect')
    @patch('paramiko.SSHClient.open_sftp')
    def test_instance_sftp_connect_close(self,
                                         paramiko_sftp_mock,
                                         paramiko_connect_mock,
                                         paramiko_close_mock):
        # TODO (akahat) remove log file code from test and other places
        release_config = "CentOS-8/master.yaml"
        log_file = os.path.expanduser(get_log_file('staging',
                                                   release_config))
        log_dir = "/".join(log_file.split("/")[:-1])
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        PromoterConfigFactory(**{'log_file': log_file})

        client = QcowConnectionClient(self.server_conf_sftp)
        assert hasattr(client, "ssh_client")

        client.connect()
        paramiko_connect_mock.assert_has_calls([
            mock.call("localhost", pkey=mock.ANY, username=os.environ['USER'])
        ])
        self.assertTrue(paramiko_connect_mock.called)
        self.assertTrue(paramiko_sftp_mock.called)

        client.close()
        self.assertFalse(paramiko_close_mock.called)

    def tearDown(self):
        super(TestQcowConnectionClient, self).tearDown()
        os.remove(self.path)


class TestQcowClient(ConfigSetup):

    def setUp(self):
        super(TestQcowClient, self).setUp()
        self.client = self.promoter.qcow_client

        self.images_root = self.client.root
        self.images_dir = self.client.images_dir
        self.previous_hash_dir = os.path.join(
            self.images_dir,
            DlrnHash(source=hashes_test_cases['aggregate']['object'][
                'valid_notimestamp']).full_hash)
        self.current_hash_dir = os.path.join(self.images_dir, "dunno")
        self.candidate_hash_dir = os.path.join(
            self.images_dir,
            DlrnHash(source=hashes_test_cases['aggregate']['object'][
                'valid']).full_hash)
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
        super(TestQcowClient, self).tearDown()
        os.chdir("/")
        shutil.rmtree(os.path.join(self.config.stage_root,
                                   self.images_root))


class TestQcowClientPromotion(TestQcowClient):

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    def test_promote_success_no_previous(self,
                                         mock_log_info,
                                         mock_log_error):
        self.client.promote(self.valid_candidate_hash, self.target_label,
                            create_previous=False, validation=False)
        promotion_link = os.path.join(self.images_dir, self.target_label)
        check_links(os, promotion_link, "test", self.candidate_hash_dir)

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

        self.client.promote(self.valid_candidate_hash, self.target_label,
                            validation=False)

        promotion_link = os.path.join(self.images_dir, self.target_label)
        previous_link = os.path.join(self.images_dir, "previous-test-label")
        previous_dir = os.path.join(
            self.images_dir,
            DlrnHash(source=hashes_test_cases['aggregate']['object'][
                'valid_notimestamp']).full_hash)
        check_links(os, promotion_link, "test", self.candidate_hash_dir,
                    previous_link=previous_link, previous_dir=previous_dir)
        self.assertFalse(mock_log_error.called)

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    def test_promote_failure_missing_candidate_dir(self,
                                                   mock_log_info,
                                                   mock_log_error):
        with self.assertRaises(PromotionError):
            self.client.promote(self.missing_candidate_hash, self.target_label)
        self.assertTrue(mock_log_error.called)


class TestQcowClientRollback(unittest.TestCase):

    @pytest.mark.xfail(reason="Not yet enabled", run=False)
    def test_rollback_pass(self):
        assert False

    @pytest.mark.xfail(reason="Not yet enabled", run=False)
    def test_rollback_fail(self):
        assert False


class TestQcowClientValidation(TestQcowClient):

    def test_validation_full_pass(self):
        expected_qcows = self.config.overcloud_images['qcow_images']
        for image_file in expected_qcows:
            with open(os.path.join(self.candidate_hash_dir, image_file), "w"):
                pass

        os.chdir(self.images_dir)
        os.symlink(self.valid_candidate_hash.full_hash, "images_promoted")

        validation_results = self.client.validate_qcows(
            self.valid_candidate_hash, name="images_promoted")

        self.assertTrue(validation_results['hash_valid'])
        self.assertEqual(validation_results['present_qcows'], expected_qcows)
        self.assertEqual(validation_results['missing_qcows'], [])
        self.assertTrue(validation_results['qcow_valid'])
        self.assertTrue(validation_results['promotion_valid'])

    def test_validate_invalid_promotion(self):
        expected_qcows = self.config.overcloud_images['qcow_images']
        for image_file in expected_qcows:
            with open(os.path.join(self.candidate_hash_dir, image_file), "w"):
                pass

        validation_results = self.client.validate_qcows(
            self.valid_candidate_hash, name="images_promoted")

        self.assertTrue(validation_results['hash_valid'])
        self.assertEqual(validation_results['present_qcows'], expected_qcows)
        self.assertEqual(validation_results['missing_qcows'], [])
        self.assertTrue(validation_results['qcow_valid'])
        self.assertFalse(validation_results['promotion_valid'])

    def test_validate_incomplete_images(self):
        expected_qcows = self.config.overcloud_images['qcow_images'].copy()

        expected_qcows.remove('undercloud.qcow2')
        for image_file in expected_qcows:
            with open(os.path.join(self.candidate_hash_dir, image_file), "w"):
                pass

        validation_results = self.client.validate_qcows(
            self.valid_candidate_hash, name="images_promoted")

        self.assertTrue(validation_results['hash_valid'])
        self.assertEqual(validation_results['present_qcows'], expected_qcows)
        self.assertEqual(validation_results['missing_qcows'],
                         ['undercloud.qcow2'])
        self.assertFalse(validation_results['qcow_valid'])
        self.assertFalse(validation_results['promotion_valid'])

    def test_validate_invalid_hash(self):
        missing_qcows = self.config.overcloud_images['qcow_images']

        validation_results = self.client.validate_qcows(
            self.missing_candidate_hash, name="images_promoted")

        self.assertFalse(validation_results['hash_valid'])
        self.assertEqual(validation_results['present_qcows'], [])
        self.assertEqual(validation_results['missing_qcows'], missing_qcows)
        self.assertFalse(validation_results['qcow_valid'])
        self.assertFalse(validation_results['promotion_valid'])
