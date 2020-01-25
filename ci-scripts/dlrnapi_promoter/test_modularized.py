import configparser
import os
import tempfile
import unittest

try:
    import mock
except ImportError:
    from unittest import mock

from config import PromoterConfig, ConfigError

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
    def test_load_ini_file_no_pass(self, fetch_current_named_hashes_mock):
        with self.assertRaises(ConfigError):
            PromoterConfig(self.filepaths['missing_section'])

    @mock.patch('config.fetch_current_named_hashes')
    def test_load_ini_file(self, fetch_current_named_hashes_mock):
        # Test for load correctness
        config = PromoterConfig(self.filepaths['correct'])
        # Test if config keys are there and have a value
        assert hasattr(config, "release"), "Missing mandatory argument"
        self.assertEqual(config.release, "master")
        self.assertEqual(config.target_registries_push, True)
        # Test if legacy config has been correctly created
        self.assertIsInstance(config.legacy_config, configparser.ConfigParser)
