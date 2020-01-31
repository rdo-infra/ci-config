import configparser
import copy
import os
import pprint
import pytest
import tempfile
import unittest
import subprocess


try:
    # Python3 imports
    from unittest.mock import Mock, patch
    import unittest.mock as mock
except ImportError:
    # Python2 imports
    from mock import Mock, patch
    import mock

from config import PromoterConfig, ConfigError
from common import PromotionError
from dlrn_client import HashChangedError
from dlrn_hash import DlrnHashError, DlrnCommitDistroHash, DlrnAggregateHash, \
    DlrnHash
from dlrnapi_promoter import main as promoter_main, arg_parser
from logic import Promoter
from qcow_client import QcowClient
from registries_client import RegistriesClient
from six import string_types

# Cases of ini configuration
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
    log_file: /dev/nul
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
    log_file: /dev/null
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


class TestCommon(unittest.TestCase):

    @pytest.mark.xfail(reason="Not implemented")
    def test_check_port_defaults(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_check_port_open_true(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_check_port_open_false(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_check_port_open_timeout(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_check_port_closed_timeout(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_check_port_closed_true(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_check_port_closed_false(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_str2bool_true(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_str2bool_false(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_str2bool_whatever(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_setup_logging_no_handlers(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_setup_logging_wrong_log_file(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_setup_logging_corrent_log_file(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_close_logging(self):
        assert False


class TestMain(unittest.TestCase):

    @pytest.mark.xfail(reason="Not implemented")
    def test_arg_parser_correct(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_arg_parser_wrong_config_file(self):
        assert False

    @mock.patch.object(Promoter, '__init__', autospec=True, return_value=None)
    @mock.patch.object(Promoter, 'promote_all', autospec=True)
    def test_main_call_new(self, start_process_mock, init_mock):

        promoter_main(cmd_line="config")

        assert init_mock.called
        assert start_process_mock.called


class TestConfigBase(unittest.TestCase):

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

    # FIXME: python2 has no unittest.assertLogs
    @patch('logging.Logger.warning')
    @patch('logging.Logger.error')
    def test_load_defective_ini_file(self, mock_error, mock_warning):
        os.environ["DLRNAPI_PASSWORD"] = "test"
        ini_config = self.filepaths['missing_parameters']
        with self.assertRaises(ConfigError):
            PromoterConfig(ini_config)
        calls = [
            mock.call('Missing parameter in configuration file: '
                      'distro_name.Using default value: centos')
        ]
        mock_warning.assert_has_calls(calls)
        calls = [
            mock.call('Invalid Log file: /dev/nul'),
            mock.call('Error in configuration file %s' % str(ini_config))
        ]
        mock_error.assert_has_calls(calls, any_order=True)

    def test_load_ini_file_no_criteria(self):
        with self.assertRaises(ConfigError):
            PromoterConfig(self.filepaths['missing_section'])

    @patch('logging.Logger.error')
    def test_load_ini_file_no_pass(self, mock_error):
        try:
            del(os.environ["DLRNAPI_PASSWORD"])
        except KeyError:
            pass
        with self.assertRaises(ConfigError):
            PromoterConfig(self.filepaths['correct'])
        calls = [
            mock.call('No dlrnapi password found in env'),
        ]
        mock_error.assert_has_calls(calls, any_order=True)

    def test_load_correct_ini_file_verify_params(self):
        self.maxDiff = None
        # Test for load correctness
        os.environ["DLRNAPI_PASSWORD"] = "test"
        config = PromoterConfig(self.filepaths['correct'])
        # Test if config keys are there and have a value
        assert hasattr(config, "release"), "Missing mandatory argument"
        assert hasattr(config, "distro_name"), "Missing mandatory argument"
        self.assertIsInstance(config.distro_name, string_types)
        self.assertEqual(config.release, "master")
        self.assertEqual(config.target_registries_push, True)
        promotion_criteria_map = {
            "current-tripleo": {
                "periodic-tripleo-centos-7-master-containers-build-push"
            }
        }
        self.assertDictEqual(promotion_criteria_map,
                             config.promotion_criteria_map)
        self.assertEqual(config.latest_hashes_count, 10)

    @pytest.mark.xfail(reason="Not implemented")
    def test_config_missing_file(self):
        assert False


class TestConfig(unittest.TestCase):

    @pytest.mark.xfail(reason="Not implemented")
    def test_get_dlrn_api_url_none(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_get_dlrn_api_url_local(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_get_dlrn_api_url_remote(self):
        assert False


# These are preparation for all the types of dlrn_hashes we are going to test
# on the following test cases.
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
different_aggregate_kwargs = dict(aggregate_hash='c', commit_hash='a',
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


class ConfigSetup(unittest.TestCase):

    def setUp(self):
        content = test_ini_configurations['correct']
        fp, self.filepath = tempfile.mkstemp(prefix="instance_test")
        with os.fdopen(fp, "w") as test_file:
            test_file.write(content)
        cli = self.filepath
        args = arg_parser(cmd_line=cli)
        os.environ["DLRNAPI_PASSWORD"] = "test"
        self.promoter = Promoter(config_file=args.config_file)

    def tearDown(self):
        os.unlink(self.filepath)


class TestDlrnClient(ConfigSetup):

    def setUp(self):
        super(TestDlrnClient, self).setUp()
        self.client = self.promoter.dlrn_client

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
        self.api_hashes_commitdistro = []
        for idx in range(2):
            api_hash = Mock(spec=commitdistrohash_valid_attrs)
            api_hash.commit_hash = "a"
            api_hash.distro_hash = "b"
            api_hash.timestamp = 1
            self.api_hashes_commitdistro.append(api_hash)
        self.api_hashes.append(self.api_hashes_commitdistro)
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
        self.api_hashes_aggregate = []
        for idx in range(2):
            api_hash = Mock(spec=aggregatehash_valid_attrs)
            api_hash.aggregate_hash = "a"
            api_hash.commit_hash = "b"
            api_hash.distro_hash = "c"
            api_hash.timestamp = 1
            self.api_hashes_aggregate.append(api_hash)
        self.api_hashes.append(self.api_hashes_aggregate)
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
            params = copy.deepcopy(self.client.hashes_params)
            params.promote_name = "test"
            hash = self.client.fetch_hashes(params, count=1)
            self.assertIn(type(hash), [DlrnCommitDistroHash,
                                       DlrnAggregateHash])
            hash_list = self.client.fetch_hashes(params, sort="timestamp",
                                                 reverse=False)
            self.assertEqual(len(hash_list), 1)
            # TODO(gcerami) test sort by timestamp and reverse

        for api_hash_list in self.api_hashes_unordered:
            promotions_get_mock.return_value = api_hash_list
            hash_list = self.client.fetch_hashes(params, sort="timestamp",
                                                 reverse=False)
            self.assertEqual(len(hash_list), 3)
            self.assertEqual(hash_list[0].timestamp, 0)
            self.assertEqual(hash_list[1].timestamp, 1)
            self.assertEqual(hash_list[2].timestamp, 2)
            hash_list = self.client.fetch_hashes(params, sort="timestamp",
                                                 reverse=True)
            self.assertEqual(hash_list[0].timestamp, 2)
            self.assertEqual(hash_list[1].timestamp, 1)
            self.assertEqual(hash_list[2].timestamp, 0)

    @patch('dlrnapi_client.DefaultApi.api_promotions_get')
    def test_fetch_promotions(self, promotions_get_mock):
        for api_hash_list in self.api_hashes:
            promotions_get_mock.return_value = api_hash_list
            params = copy.deepcopy(self.client.hashes_params)
            params.promote_name = "test"

            hash = self.client.fetch_promotions("test", count=1)
            self.assertIn(type(hash), [DlrnCommitDistroHash,
                                       DlrnAggregateHash])

    @patch('dlrnapi_client.DefaultApi.api_promotions_get')
    def test_fetch_promotions_from_hash(self, promotions_get_mock):
        promotions_get_mock.return_value = self.api_hashes_aggregate
        dlrn_hash = DlrnHash(source=sources['commitdistro']['dict'][
            'valid'])
        hash = self.client.fetch_promotions_from_hash(dlrn_hash, count=1)

        assert type(hash) == DlrnAggregateHash

        promotions_get_mock.return_value = self.api_hashes_commitdistro
        hash = self.client.fetch_promotions_from_hash(dlrn_hash, count=1)

        assert type(hash) == DlrnCommitDistroHash

    @patch('dlrnapi_client.DefaultApi.api_repo_status_get')
    def test_fetch_jobs(self, api_repo_status_get_mock):
        api_repo_status_get_mock.return_value = self.api_jobs
        hash = DlrnHash(source=self.api_hashes[0][0])
        job_list = self.client.fetch_jobs(hash)
        self.assertEqual(len(job_list), 2)
        self.assertEqual(job_list, ["job0", "job1"])

    @mock.patch('dlrn_client.DlrnClient.fetch_hashes')
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


class TestRegistriesClient(ConfigSetup):

    def setUp(self):
        super(TestRegistriesClient, self).setUp()
        self.client = self.promoter.registries_client

    def test_setup(self):
        error_msg = "Container push logfile is misplaces"
        assert self.client.logfile != "", error_msg

    @mock.patch('subprocess.check_output')
    def test_promote(self, check_output_mock):
        candidate_hash = DlrnHash(source=sources['aggregate']['dict']['valid'])
        target_label = "test"

        check_output_mock.return_value = "test log"
        self.client.promote(candidate_hash, target_label)

        assert subprocess.check_output.called
        exception = subprocess.CalledProcessError(1, 2)
        exception.output = b"test"
        check_output_mock.side_effect = exception
        with self.assertRaises(PromotionError):
            self.client.promote(candidate_hash, target_label)


class TestQcowClient(ConfigSetup):

    def setUp(self):
        super(TestQcowClient, self).setUp()
        self.client = self.promoter.qcow_client

    @mock.patch('subprocess.check_output')
    def test_promote(self, check_output_mock):
        candidate_hash = DlrnHash(source=sources['aggregate']['dict']['valid'])
        target_label = "test"

        check_output_mock.return_value = b"test log"
        self.client.promote(candidate_hash, target_label)

        assert subprocess.check_output.called
        exception = subprocess.CalledProcessError(1, 2)
        exception.output = b"test"
        check_output_mock.side_effect = exception
        with self.assertRaises(PromotionError):
            self.client.promote(candidate_hash, target_label)


class TestPromoter(ConfigSetup):

    @mock.patch('dlrn_client.DlrnClient.fetch_promotions')
    def test_no_hashes_fetched_returns_empty_list(self, fetch_hashes_mock):

        old_hashes = []
        candidate_hashes = []
        fetch_hashes_mock.side_effect = [candidate_hashes, old_hashes]

        obtained_hashes = self.promoter.select_candidates(
            'candidate_label', 'target_label')

        fetch_hashes_mock.assert_has_calls([
            mock.call('candidate_label', count=10),
        ])

        assert(len(obtained_hashes) == 0)

    @mock.patch('dlrn_client.DlrnClient.fetch_promotions')
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

        obtained_hashes = self.promoter.select_candidates(
            'candidate_label', 'target_label')
        assert(len(obtained_hashes) == 0)
        fetch_hashes_mock.assert_has_calls([
            mock.call('candidate_label', count=10),
        ])

    @mock.patch('dlrn_client.DlrnClient.fetch_promotions')
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

        obtained_hashes = self.promoter.select_candidates(
            'candidate_label', 'target_label')
        fetch_hashes_mock.assert_has_calls([
            mock.call('candidate_label', count=10),
            mock.call('target_label')
        ])

        assert(obtained_hashes == candidate_hashes)

    @mock.patch('dlrn_client.DlrnClient.fetch_promotions')
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

        obtained_hashes = self.promoter.select_candidates(
            'candidate_label', 'target_label')
        fetch_hashes_mock.assert_has_calls([
            mock.call('candidate_label', count=10),
            mock.call('target_label')
        ])

        assert(obtained_hashes == expected_hashes)
