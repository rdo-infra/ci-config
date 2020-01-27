import configparser
import os
import tempfile
import unittest

try:
    from unittest.mock import Mock, patch
    import unittest.mock as mock
except ImportError:
    from mock import Mock, patch
    import mock

from config import PromoterConfig, ConfigError
from dlrnapi_promoter import main as promoter_main
from dlrn_interface import DlrnHash, DlrnClient
from dlrnapi_promoter import Promoter
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
    log_file: /dev/null
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
    @mock.patch.object(Promoter, '__init__', autospec=True, return_value=None)
    @mock.patch.object(Promoter, 'start_process', autospec=True)
    def test_main(self, start_process_mock, init_mock, legacy_main_mock):

        promoter_main(cmd_line="config")

        assert init_mock.called
        assert start_process_mock.called

        promoter_main(cmd_line="config --force-legacy")

        assert legacy_main_mock.called


valid_dlrn_dict = dict(commit_hash='a', distro_hash='b', timestamp=1)
valid_dlrn_dict_no_timestamp = dict(commit_hash='a', distro_hash='b')
invalid_dlrn_dict = dict(commit='a', distro='b')
compare_success_dlrn_dict = dict(commit_hash='a', distro_hash='b', timestamp=1)
compare_success_dlrn_dict_no_timestamp = dict(commit_hash='a',
                                              distro_hash='b')
compare_fail_dlrn_dict = dict(commit_hash='b', distro_hash='c', timestamp=1)
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
        dh1 = DlrnHash(from_dict=valid_dlrn_dict_no_timestamp)
        dh2 = DlrnHash(from_dict=compare_success_dlrn_dict_no_timestamp)
        self.assertEqual(dh1, dh2)

    def test_properties(self):
        dh1 = DlrnHash(from_dict=valid_dlrn_dict)
        self.assertEqual(dh1.full_hash, full_hash)

    def test_dump_to_params(self):
        params = Mock()
        dh1 = DlrnHash(from_dict=valid_dlrn_dict)
        dh1.dump_to_params(params)
        self.assertEqual(params.commit_hash, dh1.commit_hash)


class TestDlrnClient(unittest.TestCase):

    def setUp(self):
        content = test_ini_configurations['correct']
        fp, self.filepath = tempfile.mkstemp(prefix="instance_test")
        with os.fdopen(fp, "w") as test_file:
            test_file.write(content)

        self.test_hash = DlrnHash(commit="cmt1", distro="dst1")
        self.api_hashes = []
        self.api_jobs = []
        # Constructs two fake lists
        # one with two identical hashes
        # the other with two different jobs
        for idx in range(2):
            api_hash = Mock()
            api_job = Mock()
            api_hash.commit_hash = "a"
            api_hash.distro_hash = "b"
            api_hash.timestamp = 1
            self.api_hashes.append(api_hash)
            api_job.job_id = "job{}".format(idx)
            api_job.timestamp = 11234567.0
            api_job.url = "https://dev/null"
            self.api_jobs.append(api_job)
        # Create an unordered list
        self.api_hashes_unordered = []
        for idx in range(3):
            api_hash = Mock()
            api_hash.commit_hash = "a{}".format(idx)
            api_hash.distro_hash = "b{}".format(idx)
            api_hash.timestamp = idx
            self.api_hashes_unordered.append(api_hash)
        self.api_hashes_unordered.append(self.api_hashes_unordered.pop(0))

        os.environ["DLRNAPI_PASSWORD"] = "test"
        config = PromoterConfig(self.filepath)
        self.client = DlrnClient(config)

    def tearDown(self):
        os.unlink(self.filepath)

    def test_hashes_to_hashes(self):
        # TODO(gcerami) test with aggregated hash
        hash_list = self.client.hashes_to_hashes(self.api_hashes)
        self.assertEqual(len(hash_list), 2)
        self.assertIsInstance(hash_list[0], DlrnHash)
        hash_list = self.client.hashes_to_hashes(self.api_hashes,
                                                 remove_duplicates=True)
        self.assertEqual(len(hash_list), 1)

    def test_fetch_hashes(self):
        # TODO(gcerami) test with aggregated hash
        # Patch the promotions_get to not query any server
        with patch.object(self.client, "promotions_get") as mocked_get:
            mocked_get.return_value = self.api_hashes
            hash_list = self.client.fetch_hashes("test")
            self.assertEqual(len(hash_list), 1)
            # TODO(gcerami) test sort by timestamp and reverse
            mocked_get.return_value = self.api_hashes_unordered
            hash_list = self.client.fetch_hashes("test", sort="timestamp")
            self.assertEqual(len(hash_list), 3)
            self.assertEqual(hash_list[0].timestamp, 0)
            self.assertEqual(hash_list[1].timestamp, 1)
            self.assertEqual(hash_list[2].timestamp, 2)
            hash_list = self.client.fetch_hashes("test", sort="timestamp",
                                                 reverse=True)
            self.assertEqual(hash_list[0].timestamp, 2)
            self.assertEqual(hash_list[1].timestamp, 1)
            self.assertEqual(hash_list[2].timestamp, 0)

    def test_fetch_jobs(self):
        # TODO(gcerami) test with aggregated hash
        # Patch the api_repo_status_get to not query any server
        with patch.object(self.client.api_instance, "api_repo_status_get") as\
                mocked_status_get:
            mocked_status_get.return_value = self.api_jobs
            job_list = self.client.fetch_jobs(self.test_hash)
            self.assertEqual(len(job_list), 2)
            self.assertEqual(job_list, ["job0", "job1"])


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


class TestPromoter(unittest.TestCase):

    def setUp(self):
        class fakeargs(object):
            pass
        self.args = fakeargs()
        content = test_ini_configurations['correct']
        fp, self.filepath = tempfile.mkstemp(prefix="instance_test")
        with os.fdopen(fp, "w") as test_file:
            test_file.write(content)
        self.args.log_file = "/dev/null"
        self.args.config_file = self.filepath

    def tearDown(self):
        os.unlink(self.filepath)

    def test_instance(self):
        os.environ["DLRNAPI_PASSWORD"] = "test"
        Promoter(self.args)


class TestPromoterLogic(unittest.TestCase):

    def setUp(self):
        content = test_ini_configurations['correct']
        fp, self.filepath = tempfile.mkstemp(prefix="instance_test")
        with os.fdopen(fp, "w") as test_file:
            test_file.write(content)
        os.environ["DLRNAPI_PASSWORD"] = "test"
        config = PromoterConfig(self.filepath)
        self.logic = PromoterLogic(config)

    def tearDown(self):
        os.unlink(self.filepath)

    @mock.patch('dlrn_interface.DlrnClient.fetch_hashes')
    def test_no_hashes_fetched_returns_empty_list(self, fetch_hashes_mock):

        old_hashes = []
        candidate_hashes = []
        fetch_hashes_mock.side_effect = [candidate_hashes, old_hashes]

        obtained_hashes = self.logic.select_candidates(
            'candidate_label', 'target_label')

        fetch_hashes_mock.assert_has_calls([
            mock.call('candidate_label', count=10,
                      sort="timestamp", reverse=True),
            mock.call('target_label')
        ])

        assert(len(obtained_hashes) == 0)

    @mock.patch('dlrn_interface.DlrnClient.fetch_hashes')
    def test_no_candidates_returns_empty_list(self, fetch_hashes_mock):

        hash_dict = {
            'timestamp': '1528085424',
            'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884eda5',
            'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77eff5'
        }
        hash = DlrnHash(from_dict=hash_dict)
        old_hashes = [hash]

        candidate_hashes = []
        fetch_hashes_mock.side_effect = [candidate_hashes, old_hashes]

        obtained_hashes = self.logic.select_candidates(
            'candidate_label', 'target_label')
        fetch_hashes_mock.assert_has_calls([
            mock.call('candidate_label', count=10,
                      sort="timestamp", reverse=True),
            mock.call('target_label')
        ])

        assert(len(obtained_hashes) == 0)

    @mock.patch('dlrn_interface.DlrnClient.fetch_hashes')
    def test_no_old_hashes_returns_candidates(self, fetch_hashes_mock):

        old_hashes = []

        hash1_dict = {
            'timestamp': '1528085424',
            'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884eda5',
            'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77eff5'
        }
        hash1 = DlrnHash(from_dict=hash1_dict)
        hash2_dict = {
            'timestamp': '1528085434',
            'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884eda6',
            'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77eff6'
        }
        hash2 = DlrnHash(from_dict=hash2_dict)
        candidate_hashes = [hash1, hash2]

        fetch_hashes_mock.side_effect = [candidate_hashes, old_hashes]

        obtained_hashes = self.logic.select_candidates(
            'candidate_label', 'target_label')
        fetch_hashes_mock.assert_has_calls([
            mock.call('candidate_label', count=10,
                      sort="timestamp", reverse=True),
            mock.call('target_label')
        ])

        assert(obtained_hashes == candidate_hashes)

    @mock.patch('dlrn_interface.DlrnClient.fetch_hashes')
    def test_old_hashes_get_filtered_from_candidates(self, fetch_hashes_mock):

        old_hashes_dicts = [
            {
                'timestamp': '1528085424',
                'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed24',
                'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef24'
            },
            {
                'timestamp': '1528085425',
                'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed25',
                'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef25'
            }
        ]

        old_hashes = []
        for hash_dict in old_hashes_dicts:
            old_hashes.append(DlrnHash(from_dict=hash_dict))

        # hashes here must be in order, as fetch_hashes now would return the
        # list in reverse timestamp order
        candidate_hashes_dicts = [
            {
                'timestamp': '1528085427',
                'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed27',
                'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef27'
            },
            {
                'timestamp': '1528085426',
                'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed26',
                'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef26'
            },
            {
                'timestamp': '1528085425',
                'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed25',
                'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef25'
            },
            {
                'timestamp': '1528085424',
                'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed24',
                'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef24'
            },
            {
                'timestamp': '1528085423',
                'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed23',
                'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef23'
            },
        ]
        candidate_hashes = []
        for hash_dict in candidate_hashes_dicts:
            candidate_hashes.append(DlrnHash(from_dict=hash_dict))

        expected_hashes_dicts = [
            {
                'timestamp': '1528085427',
                'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed27',
                'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef27'
            },
            {
                'timestamp': '1528085426',
                'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed26',
                'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef26'
            },

        ]
        expected_hashes = []
        for hash_dict in expected_hashes_dicts:
            expected_hashes.append(DlrnHash(from_dict=hash_dict))

        fetch_hashes_mock.side_effect = [candidate_hashes, old_hashes]

        obtained_hashes = self.logic.select_candidates(
            'candidate_label', 'target_label')
        fetch_hashes_mock.assert_has_calls([
            mock.call('candidate_label', count=10,
                      sort="timestamp", reverse=True),
            mock.call('target_label')
        ])

        print(obtained_hashes)
        print(expected_hashes)
        assert(obtained_hashes == expected_hashes)
