import copy
try:
    # Python3 imports
    from unittest.mock import Mock, patch
    import unittest.mock as mock
except ImportError:
    # Python2 imports
    from mock import Mock, patch
    import mock

from dlrn_client import HashChangedError
from dlrn_hash import DlrnCommitDistroHash, DlrnAggregateHash, DlrnHash
from test_promoter_common_unit import ConfigSetup, sources


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