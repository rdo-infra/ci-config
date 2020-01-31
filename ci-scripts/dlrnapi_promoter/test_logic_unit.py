try:
    # Python3 imports
    from unittest.mock import Mock, patch
    import unittest.mock as mock
except ImportError:
    # Python2 imports
    from mock import Mock, patch
    import mock

from dlrn_hash import DlrnHash
from test_promoter_common_unit import ConfigSetup


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
