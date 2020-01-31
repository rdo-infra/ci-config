import copy
import pytest
import unittest

from dlrnapi_client.rest import ApiException

from common import PromotionError
from dlrn_client import HashChangedError, DlrnClientConfig, DlrnClient
from dlrn_hash import DlrnCommitDistroHash, DlrnAggregateHash, DlrnHash
from test_unit_fixtures import hashes_test_cases

try:
    # Python3 imports
    from unittest.mock import Mock, patch
    import unittest.mock as mock
    from urllib.parse import urlparse
except ImportError:
    # Python2 imports
    from mock import Mock, patch
    import mock
    from urlparse import urlparse


class DlrnSetup(unittest.TestCase):

    def setUp(self):
        self.config = DlrnClientConfig(dlrnauth_username='foo',
                                       dlrnauth_password='bar',
                                       api_url="http://api.url",
                                       repo_url="http://repo.url")
        self.config.promotion_steps_map = {
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
        self.dlrn_hash_commitdistro1 = DlrnCommitDistroHash(commit_hash='a',
                                                            distro_hash='b')
        self.dlrn_hash_commitdistro2 = DlrnCommitDistroHash(commit_hash='c',
                                                            distro_hash='d')
        self.dlrn_hash_aggregate = DlrnAggregateHash(commit_hash='a',
                                                     distro_hash='b',
                                                     aggregate_hash='c',
                                                     timestamp=1)
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


class TestHashesToHashes(DlrnSetup):

    def test_hashes_to_hashes_no_hashes(self):
        hash_list = self.client.hashes_to_hashes([])
        self.assertEqual(hash_list, [])

    @patch('logging.Logger.debug')
    def test_hashes_to_hashes_single_hash(self, mock_log_debug):
        for api_hash_list in self.api_hashes_all_types_with_duplicates:
            dlrn_hash = self.client.hashes_to_hashes(api_hash_list, count=1)
            self.assertIn(type(dlrn_hash), [DlrnCommitDistroHash,
                                            DlrnAggregateHash])
            mock_log_debug.assert_has_calls([
                mock.call("Added hash %s built from %s", dlrn_hash,
                          api_hash_list[0])
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
            self.assertIn(type(dlrn_hash), [DlrnCommitDistroHash,
                                            DlrnAggregateHash])
            mock_log_debug.assert_has_calls([
                mock.call("Fetching hashes with criteria: %s", str_params),
                mock.call("Fetch Hashes: fetched %d hashes: %s",
                          1, dlrn_hash)
            ], any_order=True)
            self.assertFalse(mock_log_error.called)

    @patch('dlrn_client.DlrnClient.hashes_to_hashes')
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
    @patch('dlrn_client.DlrnClient.fetch_hashes')
    def test_fetch_promotions_from_label(self, fetch_hashes_mock,
                                         mock_log_debug):
        self.client.fetch_promotions("label", count=1)
        fetch_hashes_mock.asser_has_calls([
            mock.call("label", count=1)
        ])
        mock_log_debug.assert_has_calls([
            mock.call("Fetching promotion hashes from label %s", 'label')
        ])

    @patch('logging.Logger.debug')
    @patch('dlrn_client.DlrnClient.fetch_hashes')
    def test_fetch_promotions_from_hash(self, fetch_hashes_mock,
                                        mock_log_debug):
        params = copy.deepcopy(self.client.hashes_params)
        param_dlrn_hash = \
            DlrnHash(source=hashes_test_cases['commitdistro']['dict']['valid'])
        self.client.fetch_promotions_from_hash(param_dlrn_hash, count=1)
        fetch_hashes_mock.asser_has_calls([
            mock.call(param_dlrn_hash.dump_to_params(params), count=1)
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
        dlrn_hash = DlrnCommitDistroHash(commit_hash='a', distro_hash='b')
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
        dlrn_hash = DlrnCommitDistroHash(commit_hash='a', distro_hash='b')
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
        dlrn_hash = DlrnCommitDistroHash(commit_hash='a', distro_hash='b')
        job_list = self.client.fetch_jobs(dlrn_hash)
        self.assertEqual(len(job_list), 2)
        self.assertEqual(job_list, ["job0", "job1"])
        mock_log_debug.assert_has_calls([
            mock.call("Hash '%s': fetching list of successful jobs", dlrn_hash),
            mock.call("Fetched %d successful jobs for hash %s", 2, dlrn_hash),
            mock.call("%s passed on %s, logs at '%s'", 'job0',
                      '1970-01-01T01:00:00', 'https://dev/null'),
            mock.call("%s passed on %s, logs at '%s'", 'job1',
                      '1970-01-01T01:00:01', 'https://dev/null')
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


class TestNamedHashes(DlrnSetup):

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

    @pytest.mark.xfail(reason="Not implemented")
    def test_check_named_hashes_changed(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_fetch_current_named_hash(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_fetch_current_named_hash_no_store(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_update_current_named_hash(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def testpromote_hash_failed_repo_download(self):
        assert False


class TestGetHashes(DlrnSetup):

    @patch('logging.Logger.debug')
    def test_get_promotion_commitdistro_hashes_success(self, mock_log_debug):
        get_hash_method = self.client.get_promotion_commitdistro_hashes
        promotion_list = get_hash_method("",
                                         self.dlrn_hash_commitdistro1,
                                         'tripleo-ci-testing',
                                         'current-tripleo')
        self.assertNotEqual(promotion_list, [])
        self.assertTrue(mock_log_debug.called)

    @patch('logging.Logger.debug')
    def test_get_promotion_aggregate_hashes_success(self, mock_log_debug):
        promotion_list = \
            self.client.get_promotion_aggregate_hashes("",
                                                       self.dlrn_hash_aggregate,
                                                       'tripleo-ci-testing',
                                                       'current-tripleo')
        self.assertNotEqual(promotion_list, [])
        self.assertTrue(mock_log_debug.called)

    @pytest.mark.xfail(reason="Not implemented")
    def test_get_hash_from_component(self):
        # base_url = "file:///{}".format(commits.yaml)
        assert False


class TestPromoteHash(DlrnSetup):

    @pytest.mark.xfail(reason="Not implemented")
    def testpromote_hash_failed_commits_download(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def testpromote_hash_commits_invalid(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def testpromote_hash_different_api_response(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def testpromote_hash_api_error(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_promote_repo_invalid(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def testpromote_hash_success(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def testpromote_hash_failure(self):
        assert False


class TestPromote(DlrnSetup):

    @patch('logging.Logger.critical')
    @patch('logging.Logger.warning')
    @patch('logging.Logger.info')
    @patch('dlrn_client.DlrnClient.fetch_promotions')
    @patch('dlrn_client.DlrnClient.promote_hash')
    def test_promote_success(self, promote_hash_mock,
                             fetch_promotions_mock,
                             mock_log_info,
                             mock_log_warning,
                             mock_log_critical):
        fetch_promotions_mock.return_value = self.dlrn_hash_commitdistro2
        log_header = ("Dlrn promote '%s' from %s to %s:",
                      self.dlrn_hash_commitdistro1, 'tripleo-ci-testing',
                      'current-tripleo')
        self.client.promote(self.dlrn_hash_commitdistro1, 'current-tripleo',
                            candidate_label='tripleo-ci-testing')
        self.assertEqual(promote_hash_mock.call_count, 2)
        fetch_promotions_mock.assert_has_calls([
            mock.call('current-tripleo', count=1),
        ])
        mock_log_info.assert_has_calls([
            mock.call("%s moving previous promoted hash '%s' to %s"
                      "", log_header, self.dlrn_hash_commitdistro2,
                      'previous-current-tripleo'),
            mock.call("%s Attempting promotion", log_header)
        ])
        self.assertFalse(mock_log_warning.called)
        self.assertFalse(mock_log_critical.called)

    @patch('logging.Logger.critical')
    @patch('logging.Logger.warning')
    @patch('dlrn_client.DlrnClient.fetch_promotions')
    @patch('dlrn_client.DlrnClient.promote_hash')
    def test_promote_success_do_not_create_previous(self, promote_hash_mock,
                                                    fetch_promotions_mock,
                                                    mock_log_warning,
                                                    mock_log_critical):
        fetch_promotions_mock.return_value = None
        self.client.promote(self.dlrn_hash_commitdistro1, 'current-tripleo',
                            candidate_label='tripleo-ci-testing',
                            create_previous=False)
        self.assertEqual(promote_hash_mock.call_count, 1)
        self.assertFalse(mock_log_warning.called)
        self.assertFalse(mock_log_critical.called)

    @patch('logging.Logger.critical')
    @patch('logging.Logger.warning')
    @patch('logging.Logger.info')
    @patch('dlrn_client.DlrnClient.fetch_promotions')
    @patch('dlrn_client.DlrnClient.promote_hash')
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
    @patch('dlrn_client.DlrnClient.fetch_promotions')
    @patch('dlrn_client.DlrnClient.promote_hash')
    def test_promote_no_previous(self, promote_hash_mock,
                                 fetch_promotions_mock,
                                 mock_log_warning,
                                 mock_log_critical):
        fetch_promotions_mock.return_value = None
        self.client.promote(self.dlrn_hash_commitdistro1, 'current-tripleo',
                            candidate_label='tripleo-ci-testing')
        log_header = ("Dlrn promote '%s' from %s to %s:",
                      self.dlrn_hash_commitdistro1, 'tripleo-ci-testing',
                      'current-tripleo')
        mock_log_warning.assert_has_calls([
            mock.call("%s No previous promotion found", log_header)
        ])
        self.assertFalse(mock_log_critical.called)
        self.assertEqual(promote_hash_mock.call_count, 1)


class TestVotes(DlrnSetup):

    def test_get_civotes_info_commitdistro(self):
        dlrn_hash = DlrnCommitDistroHash(commit_hash='a', distro_hash='b')
        get_detail = self.client.get_civotes_info(dlrn_hash)
        urlparse(get_detail)
        detail = ("Check results at: "
                  "http://api.url/api/civotes_detail.html?commit_hash=a"
                  "&distro_hash=%b")
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
            mock.call('Dlrn voting success: %s with parameters %s',
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
        dlrn_hash = DlrnCommitDistroHash(commit_hash='a', distro_hash='b',
                                         timestamp=1)
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
            mock.call('Dlrn voting success: %s with parameters %s',
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
        dlrn_hash = DlrnCommitDistroHash(commit_hash='a', distro_hash='b',
                                         timestamp=1)
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
        dlrn_hash = DlrnCommitDistroHash(commit_hash='a', distro_hash='b',
                                         timestamp=1)
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
