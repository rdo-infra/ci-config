import pytest

from common import PromotionError

try:
    # Python3 imports
    from unittest.mock import Mock, patch
    import unittest.mock as mock
except ImportError:
    # Python2 imports
    from mock import Mock, patch
    import mock

from dlrn_hash import DlrnHash
from test_unit_fixtures import ConfigSetup


class TestPromoter(ConfigSetup):

    @pytest.mark.xfail(reason="Not Implemented")
    def test_promote_failure(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented")
    def test_promote_success(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented")
    def test_promote_no_allowed_clients(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented")
    def test_promote_label_to_label_missing_jobs(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented")
    def test_promote_label_to_label_promotion_failed(self):
        assert False

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('logging.Logger.warning')
    @patch('logic.Promoter.select_candidates')
    @patch('logic.Promoter.promote')
    def test_promote_label_to_label_no_candidates(self,
                                                  mock_promote,
                                                  mock_select_candidates,
                                                  mock_log_warning,
                                                  mock_log_info,
                                                  mock_log_error):
        mock_select_candidates.return_value = []
        promoted_pair = self.promoter.promote_label_to_label(
            'tripleo-ci-testing', 'current-tripleo')
        mock_log_warning.assert_has_calls([
            mock.call("Candidate label '%s': No candidate hashes",
                      'tripleo-ci-testing')
        ])
        self.assertFalse(mock_promote.called)
        self.assertFalse(mock_log_info.called)
        self.assertFalse(mock_log_error.called)
        self.assertEqual(promoted_pair, ())

    @pytest.mark.xfail(reason="Not Implemented")
    def test_promote_label_to_label_success(self):
        # Test that we stop at the first promotion
        assert False

    @patch('logging.Logger.info')
    @patch('dlrn_client.DlrnClient.fetch_current_named_hashes')
    @patch('logic.Promoter.promote_label_to_label')
    def test_promote_all_success(self, mock_promote_label_to_label,
                                 mock_fetch_named_hashes,
                                 mock_log_info):
        mock_promote_label_to_label.return_value = ('label', 'hash')
        promoted_pairs = self.promoter.promote_all()
        mock_fetch_named_hashes.assert_has_calls([
            mock.call(store=True)
        ])
        mock_log_info.assert_has_calls([
            mock.call('Starting promotion attempts for all labels'),
            mock.call("Candidate label '%s': Attempting promotion to '%s'",
                      'tripleo-ci-testing', 'current-tripleo'),
            mock.call("Summary: Promoted 1 hashes this round"),
            mock.call('------- -------- Promoter terminated normally')
        ])
        mock_promote_label_to_label.assert_has_calls([
            mock.call('tripleo-ci-testing', 'current-tripleo')
        ])
        self.assertEqual(promoted_pairs, [('label', 'hash')])

    @patch('logging.Logger.info')
    @patch('logging.Logger.warning')
    @patch('logging.Logger.error')
    @patch('logic.Promoter.promote_label_to_label')
    def test_promote_all_failure(self, mock_promote_label_to_label,
                                 mock_log_error,
                                 mock_log_warning,
                                 mock_log_info):
        mock_promote_label_to_label.side_effect = PromotionError
        promoted_pairs = self.promoter.promote_all()
        mock_log_error.assert_has_calls([
            mock.call("Error while trying to promote %s to %s",
                      'tripleo-ci-testing', 'current-tripleo')
        ])
        mock_log_warning.assert_has_calls([
            mock.call("Candidate label '%s': NO candidate "
                      "hash promoted to %s", 'tripleo-ci-testing',
                      'current-tripleo')
        ])
        # Ensure we terminate normally even in case of promotion failure
        mock_log_info.assert_has_calls([
            mock.call('------- -------- Promoter terminated normally')
        ])
        self.assertEqual(promoted_pairs, [])


class TestSelectCandidates(ConfigSetup):

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
