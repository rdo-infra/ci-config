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
from dlrn_interface import DlrnClient
from logic import PromoterLogic
from qcow import QcowClient
from registry import RegistryClient
from six import string_types

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

    def test_load_notini_config(self):
        with self.assertRaises(ConfigError):
            PromoterConfig(self.filepaths['not_ini'])

    def test_load_defective_ini_file(self):
        with self.assertRaises(ConfigError):
            PromoterConfig(self.filepaths['missing_parameters'])

    def test_load_ini_file_no_criteria(self):
        with self.assertRaises(ConfigError):
            PromoterConfig(self.filepaths['missing_section'])

    def test_load_ini_file_no_pass(self):
        try:
            del(os.environ["DLRNAPI_PASSWORD"])
        except KeyError:
            pass
        with self.assertRaises(ConfigError):
            PromoterConfig(self.filepaths['correct'])

    def test_load_ini_file(self):
        # Test for load correctness
        os.environ["DLRNAPI_PASSWORD"] = "test"
        config = PromoterConfig(self.filepaths['correct'])
        # Test if config keys are there and have a value
        assert hasattr(config, "release"), "Missing mandatory argument"
        assert hasattr(config, "distro_name"), "Missing mandatory argument"
        self.assertIsInstance(config.distro_name, string_types)
        self.assertEqual(config.release, "master")
        self.assertEqual(config.target_registries_push, True)
        # Test if legacy config has been correctly created
        self.assertIsInstance(config.legacy_config, configparser.ConfigParser)
        self.assertDictEqual(promotion_criteria_map,
                             config.promotion_criteria_map)
        self.assertEqual(config.latest_hashes_count, 10)


class TestMain(unittest.TestCase):

    @mock.patch('dlrnapi_promoter.legacy_main')
    @mock.patch('dlrnapi_promoter.promoter')
    @mock.patch('dlrnapi_promoter.PromoterConfig')
    def test_main(self, config_mock, promoter_mock, legacy_main_mock):

        promoter_main(cmd_line="config")

        assert promoter_mock.called

        promoter_main(cmd_line="config --force-legacy")

        assert legacy_main_mock.called


class TestDlrnClient(unittest.TestCase):

    def setUp(self):
        content = test_ini_configurations['correct']
        fp, self.filepath = tempfile.mkstemp(prefix="instance_test")
        with os.fdopen(fp, "w") as test_file:
            test_file.write(content)

    def tearDown(self):
        os.unlink(self.filepath)

    def test_instance(self):
        os.environ["DLRNAPI_PASSWORD"] = "test"
        config = PromoterConfig(self.filepath)
        DlrnClient(config)


class TestRegistryClient(unittest.TestCase):

    def setUp(self):
        content = test_ini_configurations['correct']
        fp, self.filepath = tempfile.mkstemp(prefix="instance_test")
        with os.fdopen(fp, "w") as test_file:
            test_file.write(content)

    def tearDown(self):
        os.unlink(self.filepath)

    def test_instance(self):
        os.environ["DLRNAPI_PASSWORD"] = "test"
        config = PromoterConfig(self.filepath)
        RegistryClient(config)


class TestQcowClient(unittest.TestCase):

    def setUp(self):
        content = test_ini_configurations['correct']
        fp, self.filepath = tempfile.mkstemp(prefix="instance_test")
        with os.fdopen(fp, "w") as test_file:
            test_file.write(content)

    def tearDown(self):
        os.unlink(self.filepath)

    def test_instance(self):
        os.environ["DLRNAPI_PASSWORD"] = "test"
        config = PromoterConfig(self.filepath)
        QcowClient(config)


class TestPromoterLogic(unittest.TestCase):

    def setUp(self):
        content = test_ini_configurations['correct']
        fp, self.filepath = tempfile.mkstemp(prefix="instance_test")
        with os.fdopen(fp, "w") as test_file:
            test_file.write(content)

    def tearDown(self):
        os.unlink(self.filepath)

    def test_instance(self):
        os.environ["DLRNAPI_PASSWORD"] = "test"
        config = PromoterConfig(self.filepath)
        PromoterLogic(config)
