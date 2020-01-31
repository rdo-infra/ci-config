import copy
import pytest
import unittest

from dlrnapi_client.rest import ApiException

try:
    # Python3 imports
    from unittest.mock import Mock, patch
    import unittest.mock as mock
except ImportError:
    # Python2 imports
    from mock import Mock, patch
    import mock

from dlrn_client import HashChangedError, DlrnClientConfig, DlrnClient
from dlrn_hash import DlrnCommitDistroHash, DlrnAggregateHash, DlrnHash
from test_unit_fixtures import hashes_test_cases


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
        ae = ApiException()
        ae.body = '{"message": "message"}'
        ae.status = 404
        ae.reason = "Not found"
        promotions_get_mock.side_effect = ae
        with self.assertRaises(ApiException):
            self.client.fetch_hashes(params)
        mock_log_error.assert_has_calls([
            mock.call('Exception while fetching promotions from API endpoint:'
                      ' (%s) %s: %s', ae.status, ae.reason, "message"),
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

    @pytest.mark.xfail(reason="Not implemented")
    @patch('dlrnapi_client.DefaultApi.api_repo_status_get')
    def test_fetch_jobs_api_error(self, api_repo_status_get_mock):
        api_repo_status_get_mock.return_value = self.api_jobs
        hash = DlrnHash(source=self.api_hashes_all_types_ordered[0][0])
        job_list = self.client.fetch_jobs(hash)
        self.assertEqual(len(job_list), 2)
        self.assertEqual(job_list, ["job0", "job1"])

    @pytest.mark.xfail(reason="Not implemented")
    @patch('dlrnapi_client.DefaultApi.api_repo_status_get')
    def test_fetch_jobs_no_jobs(self, api_repo_status_get_mock):
        api_repo_status_get_mock.return_value = self.api_jobs
        hash = DlrnHash(source=self.api_hashes_all_types_ordered[0][0])
        job_list = self.client.fetch_jobs(hash)
        self.assertEqual(len(job_list), 2)
        self.assertEqual(job_list, ["job0", "job1"])

    @patch('dlrnapi_client.DefaultApi.api_repo_status_get')
    def test_fetch_jobs(self, api_repo_status_get_mock):
        api_repo_status_get_mock.return_value = self.api_jobs
        hash = DlrnHash(source=self.api_hashes_all_types_ordered[0][0])
        job_list = self.client.fetch_jobs(hash)
        self.assertEqual(len(job_list), 2)
        self.assertEqual(job_list, ["job0", "job1"])


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
    def test_promote_hash_failed_repo_download(self):
        assert False


class TestPromote(DlrnSetup):

    @pytest.mark.xfail(reason="Not implemented")
    def test_promote_hash_failed_commits_download(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_promote_hash_commits_invalid(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_promote_hash_different_api_response(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_promote_hash_api_error(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_promote_repo_invalid(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_promote_hash_success(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_promote_hash_failure(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_promote_success_no_previous(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_promote_success(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_promote_previous_failed(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_promote_failure(self):
        assert False


class TestVotes(DlrnSetup):

    @pytest.mark.xfail(reason="Not implemented")
    def test_get_civotes_info(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_vote_success(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_vote_invalid_api_response(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_vote_api_error(self):
        assert False
