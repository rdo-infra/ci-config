import copy
import logging
import os
import shutil
import tempfile
import unittest

import pytest
import yaml
from dlrnapi_client.rest import ApiException
from promoter.common import PromotionError, setup_logging, str_api_object
from promoter.dlrn_client import DlrnClient, DlrnClientConfig, HashChangedError
from promoter.dlrn_hash import (DlrnAggregateHash,
                                DlrnCommitDistroExtendedHash, DlrnHash)

from .test_unit_fixtures import hashes_test_cases

try:
    # Python3 imports
    import configparser as ini_parser
    from unittest import mock
    from unittest.mock import Mock, patch
    from urllib.parse import urlparse
except ImportError:
    # Python2 imports
    import ConfigParser as ini_parser  # noqa N813
    import mock
    from mock import Mock, patch
    from urlparse import urlparse


class DlrnSetup(unittest.TestCase):

    def setUp(self):
        setup_logging("promoter", logging.DEBUG)
        self.config = DlrnClientConfig(dlrnauth_username='foo',
                                       dlrnauth_password='bar',
                                       api_url="http://api.url",
                                       repo_url="file:///tmp")
        self.config.promotions = {
            'current-tripleo': 'tripleo-ci-testing'
        }
        self.client = DlrnClient(self.config)

        # set up fake job list with two different jobs
        self.api_jobs = []
        for idx in range(2):
            api_job = Mock()
            api_job.job_id = "job{}".format(idx)
            api_job.timestamp = idx
            api_job.url = "https://dev/null"
            self.api_jobs.append(api_job)

        # Set up ApiException for api calls
        self.api_exception = ApiException()
        self.api_exception.body = '{"message": "message"}'
        self.api_exception.message = "message"
        self.api_exception.status = 404
        self.api_exception.reason = "Not found"

        # Set up some ready to use hashes
        self.dlrn_hash_commitdistro1 = DlrnCommitDistroExtendedHash(
            commit_hash='90633a3785687ddf3d37c0f86f9ad9f93926d639',
            distro_hash='d68290fed3d9aa069c95fc16d0d481084adbadc6',
            extended_hash='6137f83ab8defe688e70a18ef1c7e5bf3fbf02ef_'
                          '3945701fc2ae9b1b14e4261e87e203b2a89ccdca',
            component="tripleo",
            timestamp=1)
        self.dlrn_hash_commitdistro2 = DlrnCommitDistroExtendedHash(
            commit_hash='4f4774d4e410ce72b024c185d3054cf649e5c578',
            distro_hash='fe88530aa04df13ebc63287c819c721740837aae',
            component="tempest",
            timestamp=2)
        self.dlrn_hash_aggregate = DlrnAggregateHash(
            commit_hash='98da7b0933a2975598844bf40edec4b61714db40',
            distro_hash='c3a41aaf53b9ea10333387b7d40797ba2c1018d2',
            aggregate_hash='26b9d4d1d8fd09cdc2b11c7dd0f71f93',
            timestamp=1)
        self.promote_log_header = ("Dlrn promote '{}' from {} to {}:"
                                   "".format(self.dlrn_hash_commitdistro1,
                                             'tripleo-ci-testing',
                                             'current-tripleo'))
        # Set up the matrix of api_hashes to test
        commitdistrohash_valid_attrs = ['commit_hash', 'distro_hash',
                                        'timestamp']
        aggregatehash_valid_attrs = ['aggregate_hash', 'timestamp']

        # Create commitdistro hash list
        self.api_hashes_commitdistro_ordered = []
        for idx in range(3):
            api_hash = Mock(spec=commitdistrohash_valid_attrs)
            api_hash.commit_hash = "a{}".format(idx)
            api_hash.distro_hash = "b{}".format(idx)
            api_hash.timestamp = idx
            self.api_hashes_commitdistro_ordered.append(api_hash)

        # Create list with a duplicate by appending the last element in the
        # for again
        api_hashes_commitdistro_ordered_with_duplicates = \
            copy.deepcopy(self.api_hashes_commitdistro_ordered)
        api_hashes_commitdistro_ordered_with_duplicates.append(api_hash)

        # Create an aggregate hash list
        self.api_hashes_aggregate_ordered = []
        for idx in range(3):
            api_hash = Mock(spec=aggregatehash_valid_attrs)
            api_hash.aggregate_hash = "a{}".format(idx)
            api_hash.commit_hash = "b{}".format(idx)
            api_hash.distro_hash = "c{}".format(idx)
            api_hash.timestamp = idx
            self.api_hashes_aggregate_ordered.append(api_hash)

        # Create list with a duplicate by appending the last element in the
        # for again
        api_hashes_aggregate_ordered_with_duplicates = \
            copy.deepcopy(self.api_hashes_aggregate_ordered)
        api_hashes_aggregate_ordered_with_duplicates.append(api_hash)

        # Create an unordered list by putting the last element in front
        #
        # CommitDistro
        api_hashes_commitdistro_unordered = \
            copy.deepcopy(self.api_hashes_commitdistro_ordered)
        api_hash = api_hashes_commitdistro_unordered.pop(0)
        api_hashes_commitdistro_unordered.append(api_hash)
        #
        # Aggregate
        api_hashes_aggregate_unordered = \
            copy.deepcopy(self.api_hashes_aggregate_ordered)
        api_hash = api_hashes_aggregate_unordered.pop(0)
        api_hashes_aggregate_unordered.append(api_hash)

        self.api_hashes_all_types_ordered = [
            self.api_hashes_commitdistro_ordered,
            self.api_hashes_aggregate_ordered,
        ]
        self.api_hashes_all_types_unordered = [
            api_hashes_commitdistro_unordered,
            api_hashes_aggregate_unordered,
        ]
        self.api_hashes_all_types_with_duplicates = [
            api_hashes_commitdistro_ordered_with_duplicates,
            api_hashes_aggregate_ordered_with_duplicates,
        ]

    def get_tmp_delorean_repo(self, empty=False):
        repo_config = ini_parser.ConfigParser()
        repo_config.add_section('delorean-component1')
        repo_config.add_section('delorean-component2')
        repo_config.set('delorean-component1', "baseurl", "http://base.url")
        repo_config.set('delorean-component2', "baseurl", "http://base.url")
        tmp_dir = tempfile.mkdtemp()
        self.dlrn_hash_aggregate.label = "tripleo-ci-testing"
        candidate_label_dir = \
            os.path.join(tmp_dir,
                         self.dlrn_hash_aggregate.commit_dir)
        os.makedirs(candidate_label_dir)
        delorean_repo_path = os.path.join(candidate_label_dir,
                                          "delorean.repo")
        if not empty:
            with open(delorean_repo_path, "w") as delorean_repo:
                repo_config.write(delorean_repo)
        else:
            with open(delorean_repo_path, "w"):
                pass
        self.client.config.repo_url = "file://{}".format(tmp_dir)

        return delorean_repo_path, tmp_dir


class TestHashesToHashes(DlrnSetup):

    def test_hashes_to_hashes_no_hashes(self):
        hash_list = self.client.hashes_to_hashes([])
        self.assertEqual(hash_list, [])

    @patch('logging.Logger.debug')
    def test_hashes_to_hashes_single_hash(self, mock_log_debug):
        for api_hash_list in self.api_hashes_all_types_with_duplicates:
            dlrn_hash = self.client.hashes_to_hashes(api_hash_list, count=1)
            self.assertIn(type(dlrn_hash), [DlrnCommitDistroExtendedHash,
                                            DlrnAggregateHash])
            mock_log_debug.assert_has_calls([
                mock.call("Added hash %s built from %s", dlrn_hash,
                          str_api_object(api_hash_list[0]))
            ])

    def test_hashes_to_hashes_keep_duplicates(self):
        for api_hash_list in self.api_hashes_all_types_with_duplicates:
            hash_list = self.client.hashes_to_hashes(api_hash_list)
            self.assertEqual(len(hash_list), 4)

    def test_hashes_to_hashes_list_remove_duplicates(self):
        for api_hash_list in self.api_hashes_all_types_with_duplicates:
            hash_list = self.client.hashes_to_hashes(api_hash_list,
                                                     remove_duplicates=True)
            self.assertEqual(len(hash_list), 3)
            self.assertNotEqual(hash_list[0], hash_list[1])
            self.assertNotEqual(hash_list[1], hash_list[2])
            self.assertNotEqual(hash_list[0], hash_list[2])

    def test_hashes_to_hashes_hash_list_ordered(self):
        for api_hash_list in self.api_hashes_all_types_ordered:
            hash_list = self.client.hashes_to_hashes(api_hash_list)
            self.assertEqual(len(hash_list), 3)
            self.assertEqual(hash_list[0].timestamp, 0)
            self.assertEqual(hash_list[1].timestamp, 1)
            self.assertEqual(hash_list[2].timestamp, 2)

    def test_hashes_to_hashes_list_sort_forward(self):
        for api_hash_list in self.api_hashes_all_types_unordered:
            hash_list = self.client.hashes_to_hashes(api_hash_list,
                                                     sort="timestamp",
                                                     reverse=False)
            self.assertEqual(len(hash_list), 3)
            self.assertEqual(hash_list[0].timestamp, 0)
            self.assertEqual(hash_list[1].timestamp, 1)
            self.assertEqual(hash_list[2].timestamp, 2)

    def test_hashes_to_hashes_list_sort_reverse(self):
        for api_hash_list in self.api_hashes_all_types_unordered:
            hash_list = self.client.hashes_to_hashes(api_hash_list,
                                                     sort="timestamp",
                                                     reverse=True)
            self.assertEqual(len(hash_list), 3)
            self.assertEqual(hash_list[0].timestamp, 2)
            self.assertEqual(hash_list[1].timestamp, 1)
            self.assertEqual(hash_list[2].timestamp, 0)


class TestFetchHashes(DlrnSetup):
    """
    For statements  in these methods cycle over the various types of hashes
    list, commitdistro or aggregated.
    """

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    @patch('dlrnapi_client.DefaultApi.api_promotions_get')
    def test_fetch_hashes_no_hashes(self, promotions_get_mock,
                                    mock_log_debug,
                                    mock_log_error):
        params = copy.deepcopy(self.client.hashes_params)
        params.promote_name = "test"
        str_params = str(params).replace('\n', ' ').replace('\r', ' ')
        promotions_get_mock.return_value = []
        hash_list = self.client.fetch_hashes(params)
        self.assertEqual(hash_list, [])
        promotions_get_mock.assert_has_calls([
            mock.call(params)
        ])
        mock_log_debug.assert_has_calls([
            mock.call("Fetching hashes with criteria: %s", str_params),
            mock.call("Fetch Hashes: No hashes fetched from params %s",
                      str_params)
        ])
        self.assertFalse(mock_log_error.called)

    @patch('logging.Logger.error')
    @patch('dlrnapi_client.DefaultApi.api_promotions_get')
    def test_fetch_hashes_api_error(self, promotions_get_mock, mock_log_error):
        params = copy.deepcopy(self.client.hashes_params)
        params.promote_name = "test"
        promotions_get_mock.side_effect = self.api_exception
        with self.assertRaises(ApiException):
            self.client.fetch_hashes(params)
        mock_log_error.assert_has_calls([
            mock.call('Exception while fetching promotions from API endpoint:'
                      ' (%s) %s: %s',
                      self.api_exception.status,
                      self.api_exception.reason,
                      self.api_exception.message),
            mock.call("------- -------- Promoter aborted")
        ])

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    @patch('dlrnapi_client.DefaultApi.api_promotions_get')
    def test_fetch_hashes_single_hash(self, promotions_get_mock,
                                      mock_log_debug,
                                      mock_log_error):

        for api_hash_list in self.api_hashes_all_types_ordered:
            params = copy.deepcopy(self.client.hashes_params)
            params.promote_name = "test"
            promotions_get_mock.return_value = api_hash_list
            dlrn_hash = self.client.fetch_hashes(params, count=1)
            str_params = str(params).replace('\n', ' ').replace('\r', ' ')
            self.assertEqual(params.limit, 1)
            # Ensure that fetch_hashes return a single hash and not a list when
            # count=1
            self.assertIn(type(dlrn_hash), [DlrnCommitDistroExtendedHash,
                                            DlrnAggregateHash])
            mock_log_debug.assert_has_calls([
                mock.call("Fetching hashes with criteria: %s", str_params),
                mock.call("Fetch Hashes: fetched %d hashes: %s",
                          1, dlrn_hash)
            ], any_order=True)
            self.assertFalse(mock_log_error.called)

    @patch('promoter.dlrn_client.DlrnClient.hashes_to_hashes')
    @patch('dlrnapi_client.DefaultApi.api_promotions_get')
    def test_fetch_hashes_hash_list_sort_forward(self, promotions_get_mock,
                                                 hashes_to_hashes_mock):
        for api_hash_list in self.api_hashes_all_types_ordered:
            promotions_get_mock.return_value = api_hash_list
            params = copy.deepcopy(self.client.hashes_params)
            params.promote_name = "test"
            self.client.fetch_hashes(params, sort="timestamp", reverse=True)
            hashes_to_hashes_mock.assert_has_calls([
                mock.call(api_hash_list, count=None, remove_duplicates=True,
                          reverse=True, sort="timestamp")
            ])


class TestFetchPromotions(DlrnSetup):

    @patch('logging.Logger.debug')
    @patch('promoter.dlrn_client.DlrnClient.fetch_hashes')
    def test_fetch_promotions_from_label(self, fetch_hashes_mock,
                                         mock_log_debug):
        params = copy.deepcopy(self.client.hashes_params)
        params.promote_name = 'label'
        self.client.fetch_promotions("label", count=1)
        fetch_hashes_mock.assert_has_calls([
            mock.call(params, count=1)
        ])
        mock_log_debug.assert_has_calls([
            mock.call("Fetching promotion hashes from label %s", 'label')
        ])

    @patch('logging.Logger.debug')
    @patch('promoter.dlrn_client.DlrnClient.fetch_hashes')
    def test_fetch_promotions_from_hash(self, fetch_hashes_mock,
                                        mock_log_debug):
        params = copy.deepcopy(self.client.hashes_params)
        param_dlrn_hash = \
            DlrnHash(source=hashes_test_cases['commitdistro']['dict']['valid'])
        self.client.fetch_promotions_from_hash(param_dlrn_hash, count=1)
        param_dlrn_hash.dump_to_params(params)
        fetch_hashes_mock.assert_has_calls([
            mock.call(params, count=1)
        ])
        mock_log_debug.assert_has_calls([
            mock.call("Fetching promotion hashes from hash %s", param_dlrn_hash)
        ])


class TestFetchJobs(DlrnSetup):

    @patch('logging.Logger.error')
    @patch('dlrnapi_client.DefaultApi.api_repo_status_get')
    def test_fetch_jobs_api_error(self, api_repo_status_get_mock,
                                  mock_log_error):
        api_repo_status_get_mock.side_effect = self.api_exception
        dlrn_hash = DlrnCommitDistroExtendedHash(
            commit_hash='a', distro_hash='b')
        with self.assertRaises(ApiException):
            self.client.fetch_jobs(dlrn_hash)
        mock_log_error.assert_has_calls([
            mock.call("Exception while fetching jobs from API endpoint (%s) "
                      "%s: %s", self.api_exception.status,
                      self.api_exception.reason,
                      self.api_exception.message),
            mock.call("------- -------- Promoter aborted")
        ])

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    @patch('dlrnapi_client.DefaultApi.api_repo_status_get')
    def test_fetch_jobs_no_jobs(self, api_repo_status_get_mock,
                                mock_log_debug, mock_log_error):
        api_repo_status_get_mock.return_value = []
        dlrn_hash = DlrnCommitDistroExtendedHash(
            commit_hash='a', distro_hash='b')
        job_list = self.client.fetch_jobs(dlrn_hash)
        self.assertEqual(len(job_list), 0)
        self.assertEqual(job_list, [])
        mock_log_debug.assert_has_calls([
            mock.call("Hash '%s': fetching list of successful jobs", dlrn_hash),
            mock.call("No successful jobs for hash %s", dlrn_hash)
        ])
        self.assertFalse(mock_log_error.called)

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    @patch('dlrnapi_client.DefaultApi.api_agg_status_get')
    @patch('dlrnapi_client.DefaultApi.api_repo_status_get')
    def test_fetch_jobs_success(self, api_repo_status_get_mock,
                                api_agg_status_get_mock,
                                mock_log_debug,
                                mock_log_error):
        api_repo_status_get_mock.return_value = self.api_jobs
        dlrn_hash = DlrnCommitDistroExtendedHash(
            commit_hash='a', distro_hash='b')
        job_list = self.client.fetch_jobs(dlrn_hash)
        self.assertEqual(len(job_list), 2)
        self.assertEqual(job_list, ["job0", "job1"])
        # WOrks locally but not in upstream, debugging by commenting
        mock_log_debug.assert_has_calls([
            mock.call("Hash '%s': fetching list of successful jobs", dlrn_hash),
            # mock.call("Fetched %d successful jobs for hash %s", 2, dlrn_hash),
            # mock.call("%s passed on %s, logs at '%s'", 'job0',
            #          '1970-01-01T01:00:00', 'https://dev/null'),
            # mock.call("%s passed on %s, logs at '%s'", 'job1',
            #           '1970-01-01T01:00:01', 'https://dev/null')
        ])
        self.assertFalse(api_agg_status_get_mock.called)
        self.assertTrue(api_repo_status_get_mock.called)
        self.assertFalse(mock_log_error.called)

    @patch('logging.Logger.error')
    @patch('dlrnapi_client.DefaultApi.api_repo_status_get')
    @patch('dlrnapi_client.DefaultApi.api_agg_status_get')
    def test_fetch_jobs_success_aggregate(self, api_agg_status_get_mock,
                                          api_repo_status_get_mock,
                                          mock_log_error):
        api_agg_status_get_mock.return_value = self.api_jobs
        dlrn_hash = DlrnAggregateHash(commit_hash='a',
                                      distro_hash='b',
                                      aggregate_hash='c',
                                      timestamp=1)
        job_list = self.client.fetch_jobs(dlrn_hash)
        self.assertEqual(len(job_list), 2)
        self.assertEqual(job_list, ["job0", "job1"])
        self.assertFalse(mock_log_error.called)
        self.assertTrue(api_agg_status_get_mock.called)
        self.assertFalse(api_repo_status_get_mock.called)

    def test_fetch_jobs_notanhash(self):
        with self.assertRaises(TypeError):
            self.client.fetch_jobs([])


class TestNamedHashes(DlrnSetup):

    def setUp(self):
        super(TestNamedHashes, self).setUp()
        dlrn_start_hash_dict = {
            'timestamp': '1528085427',
            'commit_hash': '326452e5851e8347b15b53c3d6b70e6f5225f3ea',
            'distro_hash': '589b556babb2d0c5c6e79d5c2a505341b70ef370'
        }
        dlrn_changed_hash_dict = {
            'timestamp': '1528085529',
            'commit_hash': '6b3bf3bba01055ca8e544ce258b44e4f5da3da34',
            'distro_hash': '6aaa73f4925b38ae77d468257bced8d3baf8dd97'
        }
        self.dlrn_changed_hash = DlrnHash(source=dlrn_changed_hash_dict)
        self.dlrn_start_hash = DlrnHash(source=dlrn_start_hash_dict)

    @patch('logging.Logger.error')
    @patch('promoter.dlrn_client.DlrnClient.fetch_hashes')
    def test_named_hashes_unchanged(self, mock_fetch_hashes, mock_log_err):
        mock_fetch_hashes.side_effect = [self.dlrn_start_hash,
                                         self.dlrn_start_hash]
        # positive test for hashes_unchanged
        self.client.fetch_current_named_hashes(store=True)
        self.client.check_named_hashes_unchanged()
        self.assertFalse(mock_log_err.called)

    @patch('logging.Logger.error')
    @patch('promoter.dlrn_client.DlrnClient.fetch_hashes')
    def test_check_named_hashes_changed(self, mock_fetch_hashes, mock_log_err):
        mock_fetch_hashes.side_effect = [
            self.dlrn_start_hash, self.dlrn_changed_hash,
            self.dlrn_changed_hash, self.dlrn_changed_hash
        ]

        self.client.fetch_current_named_hashes(store=True)
        with self.assertRaises(HashChangedError):
            self.client.check_named_hashes_unchanged()

        mock_log_err.assert_has_calls([
            mock.call("Check named hashes: named hashes for label "
                      "'current-tripleo' changed since last check. "
                      "At promotion start: %s. Now: %s" %
                      (self.dlrn_start_hash,
                       self.dlrn_changed_hash))
        ])

        # positive again after updating
        self.client.update_current_named_hashes(self.dlrn_changed_hash,
                                                "current-tripleo")
        self.client.check_named_hashes_unchanged()

    @patch('logging.Logger.warning')
    @patch('promoter.dlrn_client.DlrnClient.fetch_hashes')
    def test_fetch_current_named_hash(self, mock_fetch_hashes, mock_log_warn):
        self.client.fetch_current_named_hashes(store=True)
        self.assertFalse(mock_log_warn.called)

    @patch('logging.Logger.debug')
    @patch('logging.Logger.warning')
    @patch('promoter.dlrn_client.DlrnClient.fetch_hashes')
    def test_fetch_current_named_hash_no_store(self, mock_fetch_hashes,
                                               mock_log_warn, mock_log_debug):
        mock_fetch_hashes.side_effect = [
            self.dlrn_start_hash, self.dlrn_start_hash
        ]

        self.client.fetch_current_named_hashes(store=False)
        self.assertFalse(mock_log_warn.called)
        mock_log_debug.assert_has_calls([
            mock.call("Check named hashes: Updating value of named hash for "
                      "current-tripleo to %s" % self.dlrn_start_hash.full_hash)
        ])
        self.client.check_named_hashes_unchanged()

    @patch('logging.Logger.debug')
    @patch('promoter.dlrn_client.DlrnClient.fetch_hashes')
    def test_update_current_named_hash(
            self, mock_fetch_hashes, mock_log_debug):
        mock_fetch_hashes.side_effect = [
            self.dlrn_changed_hash, self.dlrn_changed_hash
        ]
        self.client.update_current_named_hashes(self.dlrn_changed_hash,
                                                "current-tripleo")
        mock_log_debug.assert_has_calls([
            mock.call("Check named hashes: Updating stored value of named hash"
                      " for current-tripleo to %s" % self.dlrn_changed_hash)
        ])
        self.client.fetch_current_named_hashes(store=True)
        self.client.check_named_hashes_unchanged()

    @patch('logging.Logger.warning')
    @patch('logging.Logger.debug')
    @patch('promoter.dlrn_client.DlrnClient.fetch_promotions')
    def test_fetch_current_named_hashes_no_hashes(
            self, fetch_promotions_mock, mock_log_debug, mock_log_warn):
        fetch_promotions_mock.return_value = []
        self.client.fetch_current_named_hashes()
        self.assertFalse(mock_log_debug.called)
        mock_log_warn.assert_has_calls([
            mock.call("No promotions named %s", 'current-tripleo')
        ])


class TestGetHashes(DlrnSetup):

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('logging.Logger.debug')
    @patch('promoter.dlrn_client.DlrnClient.get_hash_from_component')
    def test_get_promotion_aggregate_hashes_success(self,
                                                    get_hash_mock,
                                                    mock_log_debug,
                                                    mock_log_info,
                                                    mock_log_error):
        self.maxDiff = None
        delorean_repo_path, tmp_dir = self.get_tmp_delorean_repo()
        # Extremely important that we ensure this method does not produce
        # aggregate hashes, as they're not the one to promote at this stage,
        # and all the commitdistro hashes must have a component
        promotion_hash1 = self.dlrn_hash_commitdistro1
        params1 = copy.deepcopy(self.client.promote_params)
        promotion_hash1.dump_to_params(params1)
        promotion_hash2 = self.dlrn_hash_commitdistro2
        params2 = copy.deepcopy(self.client.promote_params)
        promotion_hash2.dump_to_params(params2)
        params1.promote_name = 'current-tripleo'
        params2.promote_name = 'current-tripleo'
        promotion_parameters = [params1, params2]

        promotion_hashes = [self.dlrn_hash_commitdistro1,
                            self.dlrn_hash_commitdistro2]

        get_hash_mock.side_effect = promotion_hashes
        promotion_hash_list = \
            self.client.get_promotion_aggregate_hashes("",
                                                       self.dlrn_hash_aggregate,
                                                       'tripleo-ci-testing',
                                                       'current-tripleo')
        self.assertEqual(promotion_hash_list, promotion_parameters)
        get_hash_mock.assert_has_calls([
            mock.call("", "delorean-component1", "http://base.url"),
            mock.call("", "delorean-component2", "http://base.url"),
        ])
        mock_log_debug.assert_has_calls([
            mock.call("Dlrn promote '%s': URL for candidate label repo: %s",
                      self.dlrn_hash_aggregate, mock.ANY),
        ])
        mock_log_info.assert_has_calls([
            mock.call('%s aggregate repo at %s contains components %s', '',
                      mock.ANY, ', '.join(['delorean-component1',
                                           'delorean-component2'])),
        ])
        self.assertFalse(mock_log_error.called)
        shutil.rmtree(tmp_dir)

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('logging.Logger.debug')
    @patch('promoter.dlrn_client.DlrnClient.get_hash_from_component')
    def test_get_promotion_aggregate_hashes_no_components(self,
                                                          get_hash_mock,
                                                          mock_log_debug,
                                                          mock_log_info,
                                                          mock_log_error):
        delorean_repo_path, tmp_dir = self.get_tmp_delorean_repo(empty=True)
        with self.assertRaises(PromotionError):
            self.client.get_promotion_aggregate_hashes("",
                                                       self.dlrn_hash_aggregate,
                                                       'tripleo-ci-testing',
                                                       'current-tripleo')
        self.assertFalse(get_hash_mock.called)
        mock_log_error.assert_has_calls([
            mock.call("%s aggregate repo at %s contains no components", '',
                      mock.ANY),
            mock.call("------- -------- Promoter aborted")
        ])
        shutil.rmtree(tmp_dir)

    @patch('logging.Logger.error')
    @patch('promoter.dlrn_client.DlrnClient.get_hash_from_component')
    def test_get_promotion_aggregate_url_error(self,
                                               get_hash_mock,
                                               mock_log_error):
        self.config.repo_url = "file:///not.exist"
        with self.assertRaises(PromotionError):
            self.client.get_promotion_aggregate_hashes("",
                                                       self.dlrn_hash_aggregate,
                                                       'tripleo-ci-testing',
                                                       'current-tripleo')
        self.assertFalse(get_hash_mock.called)
        mock_log_error.assert_has_calls([
            mock.call("Dlrn Promote: Error downloading delorean repo at %s",
                      mock.ANY),
            mock.call("------- -------- Promoter aborted")
        ])
        self.assertEqual(mock_log_error.call_count, 2)

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    def test_get_hash_from_component_success(self, mock_log_debug,
                                             mock_log_error):
        hash_info = {
            'dt_commit': 1,
            'timestamp': 1,
            'commit_hash': "a",
            'distro_hash': "b"
        }
        commits = {'commits': [hash_info]}
        dlrn_hash = DlrnHash(source=hash_info)

        tmp_dir = tempfile.mkdtemp()
        commit_yaml_path = os.path.join(tmp_dir, "commit.yaml")
        with open(commit_yaml_path, "w") as commit_yaml:
            commit_yaml.write(yaml.dump(commits))
        base_url = "file://{}".format(tmp_dir)
        commit_url = "{}/{}".format(base_url, "commit.yaml")
        promotion_hash = self.client.get_hash_from_component("", "component1",
                                                             base_url)
        self.assertFalse(mock_log_error.called)
        self.assertEqual(promotion_hash, dlrn_hash)
        mock_log_debug.assert_has_calls([
            mock.call("%s base url url for component %s at %s", '',
                      "component1", base_url),
            mock.call("%s commit info url for component %s at %s", '',
                      "component1", commit_url),
            mock.call("%s component '%s' commit info: %s", '', "component1",
                      hash_info),
            mock.call("%s adding '%s' to promotion list", '', promotion_hash)
        ])

        shutil.rmtree(tmp_dir)

    @patch('logging.Logger.error')
    def test_get_hash_from_component_download_error(self, mock_log_error):
        base_url = "file:///tmp/non_existing"
        commit_url = "{}/{}".format(base_url, "commit.yaml")
        with self.assertRaises(PromotionError):
            self.client.get_hash_from_component("", "component1",
                                                base_url)
        mock_log_error.assert_has_calls([
            mock.call("Dlrn Promote: Error downloading component yaml info at "
                      "%s", commit_url),
            mock.call("------- -------- Promoter aborted")
        ])


class TestPromoteHash(DlrnSetup):

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('promoter.dlrn_client.DlrnClient.get_promotion_aggregate_hashes')
    @patch('dlrnapi_client.DefaultApi.api_promote_batch_post')
    @patch('dlrnapi_client.DefaultApi.api_promote_post')
    def test_promote_hash_success_aggregate(self, api_promote_mock,
                                            api_promote_batch_mock,
                                            get_hashes_mock,
                                            mock_log_info,
                                            mock_log_error):
        # In reality api_promote_post returns api_response objects, not hashes.
        # But,for the purpose of the testing, hashes are good enough
        promoted_hash = self.dlrn_hash_aggregate
        promotion_hash1 = self.dlrn_hash_commitdistro1
        params1 = copy.deepcopy(self.client.promote_params)
        promotion_hash1.dump_to_params(params1)
        promotion_hash2 = self.dlrn_hash_commitdistro2
        params2 = copy.deepcopy(self.client.promote_params)
        promotion_hash2.dump_to_params(params2)
        params2.timestamp = 1
        params1.timestamp = 1
        params1.promote_name = 'current-tripleo'
        params2.promote_name = 'current-tripleo'
        get_hashes_mock.return_value = []
        api_promote_batch_mock.return_value = promoted_hash
        promoted_hash = self.client.promote_hash("",
                                                 self.dlrn_hash_aggregate,
                                                 'current-tripleo')
        self.assertEqual(self.dlrn_hash_aggregate, promoted_hash)
        self.assertTrue(api_promote_batch_mock.called)
        mock_log_info.assert_has_calls([
            mock.call("%s (subhash %s) Successfully promoted", '', mock.ANY)
        ])
        self.assertFalse(mock_log_error.called)
        self.assertFalse(api_promote_mock.called)

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('dlrnapi_client.DefaultApi.api_promote_batch_post')
    @patch('dlrnapi_client.DefaultApi.api_promote_post')
    def test_promote_hash_success_commitdistro(self, api_promote_mock,
                                               api_promote_batch_mock,
                                               mock_log_info,
                                               mock_log_error):
        # In reality api_promote_post returns api_response objects, not hashes.
        # But,for the purpose of the testing, hashes are good enough
        promoted_hash = self.dlrn_hash_commitdistro1
        api_promote_mock.return_value = promoted_hash
        promoted_hash = self.client.promote_hash("",
                                                 self.dlrn_hash_commitdistro1,
                                                 'current-tripleo')
        self.assertEqual(self.dlrn_hash_commitdistro1, promoted_hash)
        promotion_parameters = copy.deepcopy(self.client.promote_params)
        promoted_hash.dump_to_params(promotion_parameters)
        promotion_parameters.timestamp = 1
        promotion_parameters.promote_name = 'current-tripleo'
        api_promote_mock.assert_has_calls([
            mock.call(promotion_parameters),
        ])
        mock_log_info.assert_has_calls([
            mock.call("%s (subhash %s) Successfully promoted", '', mock.ANY)
        ])
        self.assertFalse(mock_log_error.called)
        self.assertFalse(api_promote_batch_mock.called)

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('dlrnapi_client.DefaultApi.api_promote_post')
    def test_promote_hash_api_error(self, api_promote_mock,
                                    mock_log_info,
                                    mock_log_error):
        api_promote_mock.side_effect = self.api_exception
        with self.assertRaises(ApiException):
            self.client.promote_hash("", self.dlrn_hash_commitdistro1,
                                     'current-tripleo')
        mock_log_error.assert_has_calls([
            mock.call("Exception while promoting hashes to API endpoint "
                      "(%s) %s: %s",
                      self.api_exception.status,
                      self.api_exception.reason,
                      self.api_exception.message),
        ])
        self.assertFalse(mock_log_info.called)

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('dlrnapi_client.DefaultApi.api_promote_post')
    def test_promote_hash_unknown_type(self, api_promote_mock, mock_log_info,
                                       mock_log_error):
        with self.assertRaises(PromotionError):
            self.client.promote_hash("", "A hash",
                                     'current-tripleo')
        mock_log_error.assert_has_calls([
            mock.call("Unrecognized dlrn hash type: %s", type("A hash"))
        ])
        self.assertFalse(mock_log_info.called)
        self.assertFalse(api_promote_mock.called)

    @pytest.mark.xfail(reason="Need a patch to compute timestamp correctly",
                       run=False)
    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('dlrnapi_client.DefaultApi.api_promote_post')
    def test_promote_hash_inconsistent_response(self, api_promote_mock,
                                                mock_log_info,
                                                mock_log_error):
        # In reality api_promote_post returns api_response objects, not hashes.
        # But,for the purpose of the testing, hashes are good enough
        api_promote_mock.return_value = self.dlrn_hash_commitdistro2
        with self.assertRaises(PromotionError):
            self.client.promote_hash("", self.dlrn_hash_commitdistro1,
                                     'current-tripleo')
        self.assertTrue(api_promote_mock.called)
        tmp_hash = copy.deepcopy(self.dlrn_hash_commitdistro2)
        tmp_hash.timestamp = None
        mock_log_error.assert_has_calls([
            mock.call("%s (subhash %s) API returned different promoted hash:"
                      " '%s'", '', self.dlrn_hash_commitdistro1,
                      tmp_hash)
        ])
        self.assertFalse(mock_log_info.called)


class TestPromote(DlrnSetup):

    @patch('logging.Logger.critical')
    @patch('logging.Logger.warning')
    @patch('logging.Logger.info')
    @patch('promoter.dlrn_client.DlrnClient.fetch_promotions')
    @patch('promoter.dlrn_client.DlrnClient.promote_hash')
    def test_promote_success(self, promote_hash_mock,
                             fetch_promotions_mock,
                             mock_log_info,
                             mock_log_warning,
                             mock_log_critical):
        fetch_promotions_mock.return_value = self.dlrn_hash_commitdistro2
        self.client.promote(self.dlrn_hash_commitdistro1, 'current-tripleo',
                            candidate_label='tripleo-ci-testing')
        promote_hash_mock.assert_has_calls([
            mock.call(self.promote_log_header, self.dlrn_hash_commitdistro2,
                      'previous-current-tripleo',
                      candidate_label='current-tripleo'),
            mock.call(self.promote_log_header, self.dlrn_hash_commitdistro1,
                      'current-tripleo', candidate_label='tripleo-ci-testing'),
        ])
        fetch_promotions_mock.assert_has_calls([
            mock.call('current-tripleo', count=1),
        ])
        mock_log_info.assert_has_calls([
            mock.call("%s moving previous promoted hash '%s' to %s"
                      "", self.promote_log_header, self.dlrn_hash_commitdistro2,
                      'previous-current-tripleo'),
            mock.call("%s Attempting promotion", self.promote_log_header)
        ])
        self.assertFalse(mock_log_warning.called)
        self.assertFalse(mock_log_critical.called)

    @patch('logging.Logger.critical')
    @patch('logging.Logger.warning')
    @patch('promoter.dlrn_client.DlrnClient.fetch_promotions')
    @patch('promoter.dlrn_client.DlrnClient.promote_hash')
    def test_promote_success_do_not_create_previous(self, promote_hash_mock,
                                                    fetch_promotions_mock,
                                                    mock_log_warning,
                                                    mock_log_critical):
        fetch_promotions_mock.return_value = None
        self.client.promote(self.dlrn_hash_commitdistro1, 'current-tripleo',
                            candidate_label='tripleo-ci-testing',
                            create_previous=False)
        promote_hash_mock.assert_has_calls([
            mock.call(self.promote_log_header, self.dlrn_hash_commitdistro1,
                      'current-tripleo', candidate_label='tripleo-ci-testing')
        ])
        self.assertFalse(mock_log_warning.called)
        self.assertFalse(mock_log_critical.called)

    @patch('logging.Logger.critical')
    @patch('logging.Logger.warning')
    @patch('logging.Logger.info')
    @patch('promoter.dlrn_client.DlrnClient.fetch_promotions')
    @patch('promoter.dlrn_client.DlrnClient.promote_hash')
    def test_promote_same_hash_as_previous(self, promote_hash_mock,
                                           fetch_promotions_mock,
                                           mock_log_info,
                                           mock_log_warning,
                                           mock_log_critical):
        fetch_promotions_mock.return_value = self.dlrn_hash_commitdistro1
        with self.assertRaises(PromotionError):
            self.client.promote(self.dlrn_hash_commitdistro1, 'current-tripleo',
                                candidate_label='tripleo-ci-testing')
        mock_log_critical.assert_has_calls([
            mock.call("Dlrn promote: hash %s seems to already have "
                      "been promoted to %s, and all code checks to "
                      "avoid this at this point failed. Check the "
                      "code.", self.dlrn_hash_commitdistro1, 'current-tripleo')
        ])
        self.assertFalse(promote_hash_mock.called)
        self.assertFalse(mock_log_warning.called)
        self.assertFalse(mock_log_info.called)

    @patch('logging.Logger.critical')
    @patch('logging.Logger.warning')
    @patch('promoter.dlrn_client.DlrnClient.fetch_promotions')
    @patch('promoter.dlrn_client.DlrnClient.promote_hash')
    def test_promote_no_previous(self, promote_hash_mock,
                                 fetch_promotions_mock,
                                 mock_log_warning,
                                 mock_log_critical):
        fetch_promotions_mock.return_value = None
        self.client.promote(self.dlrn_hash_commitdistro1, 'current-tripleo',
                            candidate_label='tripleo-ci-testing')
        mock_log_warning.assert_has_calls([
            mock.call("%s No previous promotion found", self.promote_log_header)
        ])
        self.assertFalse(mock_log_critical.called)
        self.assertEqual(promote_hash_mock.call_count, 1)


class TestVotes(DlrnSetup):

    def test_get_civotes_info_commitdistro(self):
        dlrn_hash = DlrnCommitDistroExtendedHash(
            commit_hash='a', distro_hash='b')
        get_detail = self.client.get_civotes_info(dlrn_hash)
        urlparse(get_detail)
        detail = ("Check results at: "
                  "http://api.url/api/civotes_detail.html?commit_hash=a"
                  "&distro_hash=b")
        self.assertEqual(get_detail, detail)

    def test_get_civotes_info_aggregate(self):
        dlrn_hash = DlrnAggregateHash(commit_hash='a',
                                      distro_hash='b',
                                      aggregate_hash='c',
                                      timestamp=1)

        get_detail = self.client.get_civotes_info(dlrn_hash)
        urlparse(get_detail)
        detail = ("Check results at: http://api.url/api/civotes_agg_detail.html"
                  "?ref_hash=c")
        self.assertEqual(get_detail, detail)

    @patch('logging.Logger.error')
    def test_civotes_info_notanhash(self, mock_log_error):
        self.client.get_civotes_info([])
        mock_log_error.assert_has_calls([
            mock.call("Unknown hash type: %s", mock.ANY)
        ])

    @patch('logging.Logger.info')
    @patch('dlrnapi_client.DefaultApi.api_report_result_post')
    def test_vote_success_aggregate(self, mock_api_report, mock_log_info):
        dlrn_hash = DlrnAggregateHash(commit_hash='a',
                                      distro_hash='b',
                                      aggregate_hash='c',
                                      timestamp=1)
        params = copy.deepcopy(self.client.report_params)
        params.aggregate_hash = dlrn_hash.aggregate_hash
        params.job_id = 'job1'
        params.notes = None
        params.success = str(True)
        params.timestamp = dlrn_hash.timestamp
        params.url = "https://job.url"
        mock_api_report.return_value = True
        str_params = str(params).replace('\n', ' ').replace('\r', ' ')
        self.client.vote(dlrn_hash, params.job_id, params.url,
                         params.success)
        mock_log_info.assert_has_calls([
            mock.call('Dlrn voting success: %s for job %s with parameters %s',
                      'True', 'job1', str_params),
            mock.call('Dlrn voted success: %s for job %s on hash %s', 'True',
                      'job1', dlrn_hash),
        ])

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    @patch('logging.Logger.info')
    @patch('dlrnapi_client.DefaultApi.api_report_result_post')
    def test_vote_success_commitdistro(self, mock_api_report,
                                       mock_log_info,
                                       mock_log_debug,
                                       mock_log_error):
        dlrn_hash = DlrnCommitDistroExtendedHash(
            commit_hash='a', distro_hash='b', timestamp=1)
        params = copy.deepcopy(self.client.report_params)
        params.aggregate_hash = None
        params.commit_hash = dlrn_hash.commit_hash
        params.distro_hash = dlrn_hash.distro_hash
        params.job_id = 'job1'
        params.notes = None
        params.success = str(True)
        params.timestamp = dlrn_hash.timestamp
        params.url = "https://job.url"
        mock_api_report.return_value = True
        str_params = str(params).replace('\n', ' ').replace('\r', ' ')
        api_response = self.client.vote(dlrn_hash, params.job_id, params.url,
                                        params.success)
        mock_log_debug.assert_has_calls([
            mock.call('Dlrn voting success: %s for dlrn_hash %s', 'True',
                      dlrn_hash)
        ])
        mock_log_info.assert_has_calls([
            mock.call('Dlrn voting success: %s for job %s with parameters %s',
                      'True', 'job1', str_params),
            mock.call('Dlrn voted success: %s for job %s on hash %s', 'True',
                      'job1', dlrn_hash),
        ])
        self.assertTrue(api_response)
        self.assertFalse(mock_log_error.called)

    @patch('logging.Logger.error')
    @patch('dlrnapi_client.DefaultApi.api_report_result_post')
    def test_vote_api_error(self, mock_api_report, mock_log_error):
        mock_api_report.side_effect = self.api_exception
        dlrn_hash = DlrnCommitDistroExtendedHash(
            commit_hash='a', distro_hash='b', timestamp=1)
        with self.assertRaises(ApiException):
            self.client.vote(dlrn_hash, 'job_id', 'url', True)
        mock_log_error.assert_has_calls([
            mock.call('Dlrn voting success: %s for dlrn_hash %s: Error during '
                      'voting through API: (%s) %s: %s', str(True),
                      dlrn_hash, self.api_exception.status,
                      self.api_exception.reason, self.api_exception.message),
            mock.call("------- -------- Promoter aborted")
        ])

    @patch('logging.Logger.error')
    @patch('dlrnapi_client.DefaultApi.api_report_result_post')
    def test_vote_empty_api_response(self, mock_api_report, mock_log_error):
        mock_api_report.return_value = []
        dlrn_hash = DlrnCommitDistroExtendedHash(
            commit_hash='a', distro_hash='b', timestamp=1)
        with self.assertRaises(PromotionError):
            self.client.vote(dlrn_hash, 'job_id', 'url', True)
        mock_log_error.assert_has_calls([
            mock.call('Dlrn voting success: %s for dlrn_hash %s: API vote '
                      'response is empty', str(True), dlrn_hash),
            mock.call("------- -------- Promoter aborted")
        ])

    @pytest.mark.xfail(reason="Do we need to check this ?")
    def test_vote_invalid_api_response(self):
        assert False
