import configparser
import os
import tempfile
import unittest

try:
    import unittest.mock as mock
except ImportError:
    import mock

from config import PromoterConfig, ConfigError
from dlrnapi_promoter import main as promoter_main

test_ini_configurations = dict(
    not_ini='''
    I am not a ini file
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

    def test_load_notini_config(self):
        with self.assertRaises(ConfigError):
            PromoterConfig(self.filepaths['not_ini'])

    def test_load_ini_file(self):
        # Test for load correctness
        config = PromoterConfig(self.filepaths['correct'])
        # Test if legacy config has been correctly created
        self.assertIsInstance(config.legacy_config, configparser.ConfigParser)


class TestMain(unittest.TestCase):

    @mock.patch('dlrnapi_promoter.setup_logging')
    @mock.patch('dlrnapi_promoter.legacy_main')
    @mock.patch('dlrnapi_promoter.promoter')
    @mock.patch('dlrnapi_promoter.PromoterConfig')
    def test_main(self, config_mock, promoter_mock,
                  legacy_main_mock, setup_logging_mock):

        config_mock.legacy_config = {'main': {'log_file': "/dev/null"}}

        promoter_main(cmd_line="config")

        assert promoter_mock.called
        assert setup_logging_mock.called

        promoter_main(cmd_line="config --force-legacy")

        assert legacy_main_mock.called
