import configparser
import os
import pytest
import tempfile
import unittest

try:
    from unittest.mock import Mock, patch
    import unittest.mock as mock
except ImportError:
    from mock import Mock, patch
    import mock

from config import PromoterConfig, ConfigError
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
            self.api_hashes.append(api_hash)
            api_job.job_id = "job{}".format(idx)
            api_job.timestamp = 11234567.0
            api_job.url = "https://dev/null"
            self.api_jobs.append(api_job)
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
            mock.call('candidate_label', 'target_label', count=10,
                      sort="timestamp", reverse=True),
            mock.call('candidate_label', 'target_label')
        ])

        assert(len(obtained_hashes) == 0)

    @mock.patch('dlrn_interface.DlrnClient.fetch_hashes')
    def test_no_candidates_returns_empty_list(self, fetch_hashes_mock):

        old_hashes = [
            {
                'timestamp': '1528085424',
                'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884eda5',
                'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77eff5'
            }
        ]

        candidate_hashes = []
        fetch_hashes_mock.side_effect = [candidate_hashes, old_hashes]

        obtained_hashes = self.logic.select_candidates(
            'candidate_label', 'target_label')
        fetch_hashes_mock.assert_has_calls([
            mock.call('candidate_label', 'target_label', count=10,
                      sort="timestamp", reverse=True),
            mock.call('candidate_label', 'target_label')
        ])

        assert(len(obtained_hashes) == 0)


    @mock.patch('legacy_promoter.fetch_hashes')
    def test_no_old_hashes_returns_candidates(self, fetch_hashes_mock):

        old_hashes = []

        candidate_hashes = [
            {
                'timestamp': '1528085424',
                'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884eda5',
                'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77eff5'
            },
            {
                'timestamp': '1528085434',
                'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884eda6',
                'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77eff6'
            }
        ]
        fetch_hashes_mock.side_effect = [candidate_hashes, old_hashes]

        obtained_hashes = legacy_promoter.get_latest_hashes(
            'dlrn_api', 'promote_name', 'curent_name', 3)

        fetch_hashes_mock.assert_has_calls([
            mock.call('dlrn_api', 'curent_name', count=3),
            mock.call('dlrn_api', 'promote_name', count=-1)])

        assert(obtained_hashes == candidate_hashes)


    @mock.patch('legacy_promoter.fetch_hashes')
    def test_old_hashes_get_filtered_from_candidates(self, fetch_hashes_mock):

        old_hashes = [
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

        candidate_hashes = [
            {
                'timestamp': '1528085427',
                'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed27',
                'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef27'
            },
            {
                'timestamp': '1528085423',
                'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed23',
                'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef23'
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
                'timestamp': '1528085426',
                'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed26',
                'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef26'
            },
        ]

        expected_hashes = [
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

        fetch_hashes_mock.side_effect = [candidate_hashes, old_hashes]

        obtained_hashes = legacy_promoter.get_latest_hashes(
            'dlrn_api', 'promote_name', 'curent_name', 3)

        fetch_hashes_mock.assert_has_calls([
            mock.call('dlrn_api', 'curent_name', count=3),
            mock.call('dlrn_api', 'promote_name', count=-1)])

        assert(obtained_hashes == expected_hashes)


    @mock.patch('legacy_promoter.fetch_hashes')
    def test_named_hashes_unchanged(self, mock_fetch_hashes):
        dlrn_start_hash = {
            'timestamp': '1528085427',
            'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed27',
            'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef27'
        }
        dlrn_changed_hash = {
            'timestamp': '1528085529',
            'commit_hash': 'd1c5372341a61effdccfe5dde3e93bd21884ed27',
            'distro_hash': 'cd4fb616ac30625a51ba9156bbe70ede3d7e1921'
        }
        promote_from = {'current-tripleo': 'foo', 'current-tripleo-rdo': 'bar'}
        release = ('centos', '7')

        # positive test for hashes_unchanged
        mock_fetch_hashes.side_effect = [dlrn_start_hash, dlrn_start_hash]
        start_named_hashes = legacy_promoter.fetch_current_named_hashes(
            release, promote_from, 'dlrn')
        legacy_promoter.start_named_hashes = start_named_hashes
        mock_fetch_hashes.side_effect = [dlrn_start_hash, dlrn_start_hash]
        legacy_promoter.check_named_hashes_unchanged(release, promote_from,
                                                     'dlrn')

        # negative test
        mock_fetch_hashes.side_effect = [dlrn_start_hash, dlrn_changed_hash]
        with pytest.raises(Exception):
            legacy_promoter.check_named_hashes_unchanged(
                release, promote_from, 'dlrn')
