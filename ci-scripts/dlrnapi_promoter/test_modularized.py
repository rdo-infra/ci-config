import configparser
import os
import pytest
import tempfile
import unittest
import sys


try:
    from unittest.mock import Mock, patch
    import unittest.mock as mock
except ImportError:
    from mock import Mock, patch
    import mock

from config import PromoterConfig, ConfigError
from dlrn_interface import DlrnHash, DlrnClient, HashChangedError, DlrnHashError
from dlrn_interface import DlrnAggregateHash, DlrnCommitDistroHash
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


valid_commitdistro_kwargs = dict(commit_hash='a', distro_hash='b', timestamp=1)
valid_commitdistro_notimestamp_kwargs = dict(commit_hash='a', distro_hash='b')
invalid_commitdistro_kwargs = dict(commit='a', distro='b')
different_commitdistro_kwargs = dict(commit_hash='b', distro_hash='c',
                                     timestamp=1)
different_commitdistro_notimestamp_kwargs = dict(commit_hash='a',
                                                 distro_hash='b')
valid_aggregate_kwargs = dict(aggregate_hash='a', commit_hash='b',
                              distro_hash='c', timestamp=1)
valid_aggregate_notimestamp_kwargs = dict(aggregate_hash='a', commit_hash='b',
                                          distro_hash='c')
invalid_aggregate_kwargs = dict(aggregate='a')
different_aggregate_kwargs = dict(aggregate_hash='b', commit_hash='a',
                                  distro_hash='c', timestamp=1)
different_aggregate_notimestamp_kwargs = dict(aggregate_hash='a',
                                              commit_hash='b',
                                              distro_hash='c')
# Structured way to organize test cases by hash type and source type
# by commitdistro and aggregate hash types and by dict or object source tyep
sources = {
    'commitdistro': {
        "dict": {
            "valid": valid_commitdistro_kwargs,
            "valid_notimestamp":
                valid_commitdistro_notimestamp_kwargs,
            'invalid': invalid_commitdistro_kwargs,
            'different': different_commitdistro_kwargs,
            'different_notimestamp':
                different_commitdistro_notimestamp_kwargs
        },
        "object": {
            "valid": Mock(spec=type, **valid_commitdistro_kwargs),
            "valid_notimestamp":
                Mock(spec=type, **valid_commitdistro_notimestamp_kwargs),
            'invalid': Mock(spec=type, **invalid_commitdistro_kwargs),
            'different': Mock(spec=type, **different_commitdistro_kwargs),
            'different_notimestamp':
                Mock(spec=type, **different_commitdistro_notimestamp_kwargs)
        },
    },
    'aggregate': {
        "dict": {
            "valid": valid_aggregate_kwargs,
            "valid_notimestamp":
                valid_aggregate_notimestamp_kwargs,
            'invalid': invalid_aggregate_kwargs,
            'different': different_aggregate_kwargs,
            'different_notimestamp':
                different_aggregate_notimestamp_kwargs
        },
        "object": {
            "valid": Mock(spec=type, **valid_aggregate_kwargs),
            "valid_notimestamp":
                Mock(spec=type, **valid_aggregate_notimestamp_kwargs),
            'invalid': Mock(spec=type, **invalid_aggregate_kwargs),
            'different': Mock(spec=type, **different_aggregate_kwargs),
            'different_notimestamp':
                Mock(spec=type, **different_aggregate_notimestamp_kwargs),
        },
    },
}


class TestDlrnHashSubClasses(unittest.TestCase):

    def test_build_valid(self):
        for hash_type, source_types in sources.items():
            values = source_types['dict']['valid']
            if hash_type == "commitdistro":
                dh = DlrnCommitDistroHash(commit_hash=values['commit_hash'],
                                          distro_hash=values['distro_hash'],
                                          timestamp=values['timestamp'])
                self.assertEqual(dh.commit_hash,
                                 source_types['dict']['valid']['commit_hash'])
                self.assertEqual(dh.distro_hash,
                                 source_types['dict']['valid']['distro_hash'])
            elif hash_type == "aggregate":
                aggregate_hash = source_types['dict']['valid'][
                    'aggregate_hash']
                dh = DlrnAggregateHash(aggregate_hash=values['aggregate_hash'],
                                       commit_hash=values['commit_hash'],
                                       distro_hash=values['distro_hash'],
                                       timestamp=values['timestamp'])
                self.assertEqual(dh.aggregate_hash, aggregate_hash)
        self.assertEqual(dh.timestamp,
                         source_types['dict']['valid']['timestamp'])

    def test_build_valid_from_source(self):
        for hash_type, source_types in sources.items():
            values = source_types['dict']['valid']
            if hash_type == "commitdistro":
                dh = DlrnCommitDistroHash(source=values)
                self.assertEqual(dh.commit_hash,
                                 source_types['dict']['valid']['commit_hash'])
                self.assertEqual(dh.distro_hash,
                                 source_types['dict']['valid']['distro_hash'])
            elif hash_type == "aggregate":
                aggregate_hash = source_types['dict']['valid'][
                    'aggregate_hash']
                dh = DlrnAggregateHash(source=values)
                self.assertEqual(dh.aggregate_hash, aggregate_hash)
        self.assertEqual(dh.timestamp,
                         source_types['dict']['valid']['timestamp'])

    def test_build_invalid_from_source(self):
        with self.assertRaises(DlrnHashError):
            source = sources['commitdistro']['dict']['invalid']
            DlrnCommitDistroHash(source=source)
        with self.assertRaises(DlrnHashError):
            source = sources['aggregate']['dict']['invalid']
            DlrnAggregateHash(source=source)


class TestDlrnHash(unittest.TestCase):

    def test_create_from_values(self):
        for hash_type, source_types in sources.items():
            dh = DlrnHash(**source_types['dict']['valid'])
            print(hash_type)
            if hash_type == "commitdistro":
                self.assertEqual(type(dh), DlrnCommitDistroHash)
            elif hash_type == 'aggregate':
                self.assertEqual(type(dh), DlrnAggregateHash)

    def test_build_invalid(self):
        with self.assertRaises(DlrnHashError):
            DlrnHash(source=[])

    def test_create_from_dict(self):
        for hash_type, source_types in sources.items():
            dh = DlrnHash(source=source_types['dict']['valid'])
            if hash_type == "commitdistro":
                self.assertEqual(type(dh), DlrnCommitDistroHash)
            elif hash_type == "aggregate":
                self.assertEqual(type(dh), DlrnAggregateHash)
            with self.assertRaises(DlrnHashError):
                DlrnHash(source=source_types['dict']['invalid'])

    def test_create_from_object(self):
        # Prevent Mock class to identify as dict
        for hash_type, source_types in sources.items():
            source_valid = source_types['object']['valid']
            DlrnHash(source=source_valid)
            with self.assertRaises(DlrnHashError):
                source_invalid = source_types['object']['invalid']
                DlrnHash(source=source_invalid)

    def test_comparisons(self):
        non_dh = {}
        for hash_type, source_types in sources.items():
            dh1 = DlrnHash(source=source_types['object']['valid'])
            dh2 = DlrnHash(source=source_types['object']['valid'])
            self.assertEqual(dh1, dh2)
            dh2 = DlrnHash(source=source_types['object']['different'])
            self.assertNotEqual(dh1, dh2)
            with self.assertRaises(TypeError):
                (dh1 == non_dh)
            with self.assertRaises(TypeError):
                (dh1 != non_dh)
            dh1 = DlrnHash(source=source_types['object']['valid_notimestamp'])
            dh2 = DlrnHash(source=source_types['object']['valid_notimestamp'])
            self.assertEqual(dh1, dh2)

    def test_properties(self):
        for hash_type, source_types in sources.items():
            source = source_types['object']['valid']
            dh = DlrnHash(source=source)
            if hash_type == "commitdistro":
                full_hash = "{}_{}".format(source.commit_hash,
                                           source.distro_hash[:8])
                self.assertEqual(dh.full_hash, full_hash)
            elif hash_type == "aggregate":
                self.assertEqual(dh.full_hash, source.aggregate_hash)

    def test_dump_to_params(self):
        for hash_type, source_types in sources.items():
            params = Mock()
            dh = DlrnHash(source=source_types['object']['valid'])
            dh.dump_to_params(params)
            if hash_type == "commitdistro":
                self.assertEqual(params.commit_hash, dh.commit_hash)
                self.assertEqual(params.distro_hash, dh.distro_hash)
            elif hash_type == "aggregate":
                self.assertEqual(params.aggregate_hash, dh.aggregate_hash)
            self.assertEqual(params.timestamp, dh.timestamp)


class TestDlrnClient(unittest.TestCase):

    def setUp(self):
        content = test_ini_configurations['correct']
        fp, self.filepath = tempfile.mkstemp(prefix="instance_test")
        with os.fdopen(fp, "w") as test_file:
            test_file.write(content)
        os.environ["DLRNAPI_PASSWORD"] = "test"
        config = PromoterConfig(self.filepath)
        self.client = DlrnClient(config)

        # set up fake job list with two different jobs
        self.api_jobs = []
        for idx in range(2):
            api_job = Mock()
            api_job.job_id = "job{}".format(idx)
            api_job.timestamp = idx
            api_job.url = "https://dev/null"
            self.api_jobs.append(api_job)

        # Set up the matrix of api_hashes to test
        commitdistrohash_valid_attrs = ['commit_hash', 'distro_hash',
                                        'timestamp']
        aggregatehash_valid_attrs = ['aggregate_hash', 'timestamp']
        self.api_hashes = []
        self.api_hashes_unordered = []

        # set up fake dlrn api hashes commitdistro objects
        api_hashes_commitdistro = []
        for idx in range(2):
            api_hash = Mock(spec=commitdistrohash_valid_attrs)
            api_hash.commit_hash = "a"
            api_hash.distro_hash = "b"
            api_hash.timestamp = 1
            api_hashes_commitdistro.append(api_hash)
        self.api_hashes.append(api_hashes_commitdistro)
        # Create an unordered list
        api_hashes_commitdistro_unordered = []
        for idx in range(3):
            api_hash = Mock(spec=commitdistrohash_valid_attrs)
            api_hash.commit_hash = "a{}".format(idx)
            api_hash.distro_hash = "b{}".format(idx)
            api_hash.timestamp = idx
            api_hashes_commitdistro_unordered.append(api_hash)
        api_hash = api_hashes_commitdistro_unordered.pop(0)
        api_hashes_commitdistro_unordered.append(api_hash)
        self.api_hashes_unordered.append(api_hashes_commitdistro_unordered)

        # set up fake dlrn api aggregaed hashes objects
        api_hashes_aggregate = []
        for idx in range(2):
            api_hash = Mock(spec=aggregatehash_valid_attrs)
            api_hash.aggregate_hash = "a"
            api_hash.commit_hash = "b"
            api_hash.distro_hash = "c"
            api_hash.timestamp = 1
            api_hashes_aggregate.append(api_hash)
        self.api_hashes.append(api_hashes_aggregate)
        # Create an unordered list
        api_hashes_aggregate_unordered = []
        for idx in range(3):
            api_hash = Mock(spec=aggregatehash_valid_attrs)
            api_hash.aggregate_hash = "a{}".format(idx)
            api_hash.commit_hash = "b{}".format(idx)
            api_hash.distro_hash = "c{}".format(idx)
            api_hash.timestamp = idx
            api_hashes_aggregate_unordered.append(api_hash)
        api_hash = api_hashes_aggregate_unordered.pop(0)
        api_hashes_aggregate_unordered.append(api_hash)
        self.api_hashes_unordered.append(api_hashes_aggregate_unordered)

    def tearDown(self):
        os.unlink(self.filepath)

    def test_hashes_to_hashes(self):
        # tests both commitdistro and aggregate
        for api_hash_list in self.api_hashes:
            hash_list = self.client.hashes_to_hashes(api_hash_list)
            self.assertEqual(len(hash_list), 2)
            self.assertIn(type(hash_list[0]), [DlrnCommitDistroHash,
                                               DlrnAggregateHash])
            hash_list = self.client.hashes_to_hashes(api_hash_list,
                                                     remove_duplicates=True)
            self.assertEqual(len(hash_list), 1)

    @patch('dlrnapi_client.DefaultApi.api_promotions_get')
    def test_fetch_hashes(self, promotions_get_mock):
        # Patch the promotions_get to not query any server
        for api_hash_list in self.api_hashes:
            promotions_get_mock.return_value = api_hash_list
            # Ensure that fetch_hashes return a single hash and not a list when
            # count=1
            hash = self.client.fetch_hashes("test", count=1)
            self.assertIn(type(hash), [DlrnCommitDistroHash,
                                       DlrnAggregateHash])
            hash_list = self.client.fetch_hashes("test")
            self.assertEqual(len(hash_list), 1)
            # TODO(gcerami) test sort by timestamp and reverse

        for api_hash_list in self.api_hashes_unordered:
            promotions_get_mock.return_value = api_hash_list
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

    @patch('dlrnapi_client.DefaultApi.api_repo_status_get')
    def test_fetch_jobs(self, api_repo_status_get_mock):
        api_repo_status_get_mock.return_value = self.api_jobs
        print(type(self.api_hashes[0][0]))
        hash = DlrnHash(source=self.api_hashes[0][0])
        job_list = self.client.fetch_jobs(hash)
        self.assertEqual(len(job_list), 2)
        self.assertEqual(job_list, ["job0", "job1"])

    @mock.patch('dlrn_interface.DlrnClient.fetch_hashes')
    def test_named_hashes_unchanged(self, mock_fetch_hashes):
        dlrn_start_hash_dict = {
            'timestamp': '1528085427',
            'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed27',
            'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef27'
        }
        dlrn_changed_hash_dict = {
            'timestamp': '1528085529',
            'commit_hash': 'd1c5372341a61effdccfe5dde3e93bd21884ed27',
            'distro_hash': 'cd4fb616ac30625a51ba9156bbe70ede3d7e1921'
        }
        dlrn_changed_hash = DlrnHash(source=dlrn_changed_hash_dict)
        dlrn_start_hash = DlrnHash(source=dlrn_start_hash_dict)

        mock_fetch_hashes.side_effect = [dlrn_start_hash, dlrn_start_hash,
                                         dlrn_changed_hash, dlrn_changed_hash]
        # positive test for hashes_unchanged
        self.client.fetch_current_named_hashes(store=True)
        self.client.check_named_hashes_unchanged()

        # negative test
        with self.assertRaises(HashChangedError):
            self.client.check_named_hashes_unchanged()

        # positive again after updating
        self.client.update_current_named_hashes(dlrn_changed_hash,
                                                "current-tripleo")
        self.client.check_named_hashes_unchanged()


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
        hash = DlrnHash(source=hash_dict)
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
        hash1 = DlrnHash(source=hash1_dict)
        hash2_dict = {
            'timestamp': '1528085434',
            'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884eda6',
            'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77eff6'
        }
        hash2 = DlrnHash(source=hash2_dict)
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
            old_hashes.append(DlrnHash(source=hash_dict))

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
            candidate_hashes.append(DlrnHash(source=hash_dict))

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
            expected_hashes.append(DlrnHash(source=hash_dict))

        fetch_hashes_mock.side_effect = [candidate_hashes, old_hashes]

        obtained_hashes = self.logic.select_candidates(
            'candidate_label', 'target_label')
        fetch_hashes_mock.assert_has_calls([
            mock.call('candidate_label', count=10,
                      sort="timestamp", reverse=True),
            mock.call('target_label')
        ])

        assert(obtained_hashes == expected_hashes)
