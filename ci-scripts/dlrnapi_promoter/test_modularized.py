import configparser
import os
import tempfile
import unittest

try:
    import mock
except ImportError:
    from unittest import mock

from config import PromoterConfig, ConfigError
from dlrn_interface import DlrnHash


test_ini_configurations = dict(
    not_ini='''
    I am not a ini file
    ''',
    missing_parameters='''
    [main]
    distro_version: 7
    release: master
    api_url: https://trunk.rdoproject.org/api-centos-master-uc
    username: ciuser
    dry_run: no
    log_file: ~/promoter_logs/centos7_master.log
    latest_hashes_count: 10
    manifest_push: true

    [promote_from]
    current-tripleo: tripleo-ci-testing

    [current-tripleo]
    periodic-tripleo-centos-7-master-containers-build-push
    ''',
    missing_section='''
    [main]
    # missing mandatory parameters and sections
    distro_name: centos
    distro_version: 7
    release: master
    api_url: https://trunk.rdoproject.org/api-centos-master-uc
    username: ciuser
    dry_run: no
    log_file: ~/promoter_logs/centos7_master.log
    latest_hashes_count: 10
    manifest_push: true

    [promote_from]
    current-tripleo: tripleo-ci-testing
    ''',
    correct='''
    [main]
    distro_name: centos
    distro_version: 7
    release: master
    api_url: https://trunk.rdoproject.org/api-centos-master-uc
    username: ciuser
    dry_run: no
    log_file: ~/promoter_logs/centos7_master.log
    latest_hashes_count: 10
    manifest_push: true

    [promote_from]
    current-tripleo: tripleo-ci-testing

    [current-tripleo]
    periodic-tripleo-centos-7-master-containers-build-push
    ''',
)

promotion_criteria_map = {
    "current-tripleo": set(["periodic-tripleo-centos-7-master-containers-build"
                            "-push"])
}


class TestConfig(unittest.TestCase):

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

    @mock.patch('config.fetch_current_named_hashes')
    def test_load_notini_config(self, fetch_current_named_hashes_mock):
        with self.assertRaises(ConfigError):
            PromoterConfig(self.filepaths['not_ini'])

    @mock.patch('config.fetch_current_named_hashes')
    def test_load_defective_ini_file(self, fetch_current_named_hashes_mock):
        with self.assertRaises(ConfigError):
            PromoterConfig(self.filepaths['missing_parameters'])

    @mock.patch('config.fetch_current_named_hashes')
    def test_load_ini_file_no_criteria(self, fetch_current_named_hashes_mock):
        with self.assertRaises(ConfigError):
            PromoterConfig(self.filepaths['missing_section'])

    @mock.patch('config.fetch_current_named_hashes')
    def test_load_ini_file_no_pass(self, fetch_current_named_hashes_mock):
        try:
            del(os.environ["DLRNAPI_PASSWORD"])
        except KeyError:
            pass
        with self.assertRaises(ConfigError):
            PromoterConfig(self.filepaths['correct'])

    @mock.patch('config.fetch_current_named_hashes')
    def test_load_ini_file(self, fetch_current_named_hashes_mock):
        # Test for load correctness
        os.environ["DLRNAPI_PASSWORD"] = "test"
        config = PromoterConfig(self.filepaths['correct'])
        # Test if config keys are there and have a value
        assert hasattr(config, "release"), "Missing mandatory argument"
        self.assertEqual(config.release, "master")
        self.assertEqual(config.target_registries_push, True)
        # Test if legacy config has been correctly created
        self.assertIsInstance(config.legacy_config, configparser.ConfigParser)
        self.assertDictEqual(promotion_criteria_map,
                             config.promotion_criteria_map)

valid_dlrn_dict = dict(commit_hash='a', distro_hash='b')
invalid_dlrn_dict = dict(commit='a', distro='b')
compare_success_dlrn_dict = dict(commit_hash='a', distro_hash='b')
compare_fail_dlrn_dict = dict(commit_hash='b', distro_hash='c')
full_hash = "a_b"


class TestDlrnHash(unittest.TestCase):

    def test_create_from_values(self):
        dh = DlrnHash(commit=valid_dlrn_dict['commit_hash'],
                      distro=valid_dlrn_dict['distro_hash'])
        self.assertEqual(dh.commit_hash, valid_dlrn_dict['commit_hash'])
        self.assertEqual(dh.distro_hash, valid_dlrn_dict['distro_hash'])

    def test_create_from_dict(self):
        with self.assertRaises(KeyError):
            DlrnHash(from_dict=invalid_dlrn_dict)
        dh = DlrnHash(from_dict=valid_dlrn_dict)
        self.assertEqual(dh.commit_hash, valid_dlrn_dict['commit_hash'])
        self.assertEqual(dh.distro_hash, valid_dlrn_dict['distro_hash'])

    def test_create_from_api(self):
        pass

    def test_comparisons(self):
        dh1 = DlrnHash(from_dict=valid_dlrn_dict)
        dh2 = DlrnHash(from_dict=compare_success_dlrn_dict)
        self.assertEqual(dh1, dh2)
        dh2 = DlrnHash(from_dict=compare_fail_dlrn_dict)
        self.assertNotEqual(dh1, dh2)
        with self.assertRaises(TypeError):
            (dh1 == invalid_dlrn_dict)
            (dh1 != invalid_dlrn_dict)

    def test_properties(self):
        dh1 = DlrnHash(from_dict=valid_dlrn_dict)
        self.assertEqual(dh1.full_hash, full_hash)


