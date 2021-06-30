from common import PromotionError
from dlrn_client import HashChangedError

try:
    # Python3 imports
    from unittest import mock
    from unittest.mock import patch
except ImportError:
    # Python2 imports
    from mock import patch
    import mock

from dlrn_hash import DlrnCommitDistroExtendedHash, DlrnHash
from test_unit_fixtures import ConfigSetup


class TestPromote(ConfigSetup):

    @patch('logging.Logger.exception')
    @patch('logging.Logger.error')
    @patch('dlrn_client.DlrnClient.check_named_hashes_unchanged')
    @patch('dlrn_client.DlrnClient.promote')
    @patch('registries_client.RegistriesClient.promote')
    @patch('qcow_client.QcowClient.promote')
    def test_promote_failure(self,
                             mock_qcow_client,
                             mock_registries_client,
                             mock_dlrn_client,
                             mock_check_named_hashes,
                             mock_log_error,
                             mock_log_exception):
        mock_dlrn_client.return_value = None
        mock_qcow_client.side_effect = PromotionError
        mock_registries_client.return_value = None
        mock_check_named_hashes.return_value = None
        candidate_hash = DlrnCommitDistroExtendedHash(commit_hash='a',
                                                      distro_hash='b')
        with self.assertRaises(PromotionError):
            self.promoter.promote(candidate_hash, 'tripleo-ci-testing',
                                  'tripleo-ci-staging-promoted')

        mock_log_error.assert_has_calls([
            mock.call("Candidate hash '%s': client %s FAILED promotion attempt "
                      "to %s"
                      "", candidate_hash, 'qcow_client',
                      'tripleo-ci-staging-promoted')
        ])
        self.assertTrue(mock_log_exception.called)
        self.assertTrue(mock_registries_client.called)
        self.assertTrue(mock_qcow_client.called)
        self.assertFalse(mock_dlrn_client.called)

    @patch('logging.Logger.debug')
    @patch('dlrn_client.DlrnClient.check_named_hashes_unchanged')
    @patch('dlrn_client.DlrnClient.promote')
    @patch('registries_client.RegistriesClient.promote')
    @patch('qcow_client.QcowClient.promote')
    def test_promote_only_dlrn_client_allowed(self,
                                              mock_qcow_client,
                                              mock_registries_client,
                                              mock_dlrn_client,
                                              mock_check_named_hashes,
                                              mock_log_debug):
        candidate_hash = DlrnCommitDistroExtendedHash(commit_hash='a',
                                                      distro_hash='b')
        mock_check_named_hashes.return_value = None
        self.promoter.promote(candidate_hash, 'tripleo-ci-testing',
                              'tripleo-ci-staging-promoted',
                              allowed_clients=['dlrn_client'])
        mock_log_debug.assert_has_calls([
            mock.call("Candidate hash '%s': clients allowed to promote: %s",
                      candidate_hash, 'dlrn_client'),
        ])
        self.assertFalse(mock_registries_client.called)
        self.assertFalse(mock_qcow_client.called)
        self.assertTrue(mock_dlrn_client.called)

    @patch('logging.Logger.warning')
    @patch('logging.Logger.debug')
    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('dlrn_client.DlrnClient.check_named_hashes_unchanged')
    @patch('dlrn_client.DlrnClient.promote')
    @patch('registries_client.RegistriesClient.promote')
    @patch('qcow_client.QcowClient.promote')
    def test_promote_success(self,
                             mock_qcow_client,
                             mock_registries_client,
                             mock_dlrn_client,
                             mock_check_named_hashes,
                             mock_log_info,
                             mock_log_error,
                             mock_log_debug,
                             mock_log_warning):
        candidate_hash = DlrnCommitDistroExtendedHash(commit_hash='a',
                                                      distro_hash='b')
        mock_check_named_hashes.return_value = None

        # The order here is VERY important, and we MUST ensure it's respected
        allowed_clients = [
            'registries_client',
            'qcow_client',
            'dlrn_client'
        ]
        mock_dlrn_client.return_value = None
        mock_qcow_client.return_value = None
        mock_registries_client.return_value = None
        promoted_pair = \
            self.promoter.promote(candidate_hash, 'tripleo-ci-testing',
                                  'tripleo-ci-staging-promoted')
        mock_log_debug.assert_has_calls([
            mock.call("Candidate hash '%s': clients allowed to promote: %s",
                      candidate_hash, ', '.join(allowed_clients)),
            mock.call("Candidate hash '%s': client %s SUCCESSFUL promotion",
                      candidate_hash, allowed_clients[0]),
            mock.call("Candidate hash '%s': client %s SUCCESSFUL promotion",
                      candidate_hash, allowed_clients[1]),
            mock.call("Candidate hash '%s': client %s SUCCESSFUL promotion",
                      candidate_hash, allowed_clients[2]),
        ])
        mock_log_info.assert_has_calls([
            mock.call("Candidate hash '%s': attempting promotion",
                      candidate_hash),
            mock.call("Candidate hash '%s': SUCCESSFUL promotion to %s",
                      candidate_hash, 'tripleo-ci-staging-promoted'),
        ])
        self.assertFalse(mock_log_warning.called)
        self.assertFalse(mock_log_error.called)
        self.assertTrue(mock_check_named_hashes.called)
        self.assertTrue(mock_registries_client.called)
        self.assertTrue(mock_qcow_client.called)
        self.assertTrue(mock_dlrn_client.called)
        self.assertEqual(promoted_pair,
                         (candidate_hash, 'tripleo-ci-staging-promoted'))

    @patch('logging.Logger.debug')
    @patch('dlrn_client.DlrnClient.check_named_hashes_unchanged')
    @patch('dlrn_client.DlrnClient.promote')
    @patch('registries_client.RegistriesClient.promote')
    @patch('qcow_client.QcowClient.promote')
    def test_promote_check_named_hashes_failed(self,
                                               mock_qcow_client,
                                               mock_registries_client,
                                               mock_dlrn_client,
                                               mock_check_named_hashes,
                                               mock_log_debug):
        candidate_hash = DlrnCommitDistroExtendedHash(commit_hash='a',
                                                      distro_hash='b')
        mock_check_named_hashes.side_effect = HashChangedError
        with self.assertRaises(HashChangedError):
            self.promoter.promote(candidate_hash, 'tripleo-ci-testing',
                                  'tripleo-ci-staging-promoted')
        self.assertFalse(mock_registries_client.called)
        self.assertFalse(mock_qcow_client.called)
        self.assertFalse(mock_dlrn_client.called)


class TestPromoteLabelToLabel(ConfigSetup):

    @patch('logging.Logger.debug')
    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('logging.Logger.warning')
    @patch('logic.Promoter.select_candidates')
    @patch('logic.Promoter.promote')
    @patch('dlrn_client.DlrnClient.fetch_jobs')
    @patch('dlrn_client.DlrnClient.get_civotes_info')
    def test_promote_label_to_label_missing_jobs(self,
                                                 mock_civotes,
                                                 mock_fetch_jobs,
                                                 mock_promote,
                                                 mock_select_candidates,
                                                 mock_log_warning,
                                                 mock_log_info,
                                                 mock_log_error,
                                                 mock_log_debug):
        ci_votes = "http://host.to/detailspage.html"
        mock_civotes.return_value = ci_votes
        successful_jobs = [
            'periodic-tripleo-centos-7-master-containers-build-push',
        ]
        mock_fetch_jobs.return_value = successful_jobs
        candidate_hash = DlrnCommitDistroExtendedHash(commit_hash='a',
                                                      distro_hash='b')
        mock_select_candidates.return_value = [
            candidate_hash
        ]
        promoted_pair = self.promoter.promote_label_to_label(
            'tripleo-ci-testing', 'tripleo-ci-staging-promoted')
        mock_log_warning.assert_has_calls([
            mock.call("Candidate hash '%s': criteria NOT met for promotion to "
                      "%s", candidate_hash, 'tripleo-ci-staging-promoted'),
        ])
        mock_log_info.assert_has_calls([
            mock.call("Candidate label '%s': %d candidates",
                      'tripleo-ci-testing', 1),
            mock.call("Candidate label '%s': Checking candidates that meet "
                      "promotion criteria for target label '%s'",
                      'tripleo-ci-testing', 'tripleo-ci-staging-promoted'),
            mock.call("Candidate hash '%s': vote details page - %s",
                      candidate_hash, ci_votes),
        ])
        self.assertFalse(mock_promote.called)
        self.assertFalse(mock_log_error.called)
        self.assertEqual(promoted_pair, ())

    @patch('logging.Logger.error')
    @patch('logging.Logger.warning')
    @patch('logic.Promoter.select_candidates')
    @patch('logic.Promoter.promote')
    @patch('dlrn_client.DlrnClient.fetch_jobs')
    @patch('dlrn_client.DlrnClient.get_civotes_info')
    def test_promote_label_to_label_missing_jobs_no_successful(
            self,
            mock_civotes,
            mock_fetch_jobs,
            mock_promote,
            mock_select_candidates,
            mock_log_warning,
            mock_log_error):
        ci_votes = "http://host.to/detailspage.html"
        mock_civotes.return_value = ci_votes
        successful_jobs = []
        mock_fetch_jobs.return_value = successful_jobs
        candidate_hash = DlrnCommitDistroExtendedHash(commit_hash='a',
                                                      distro_hash='b')
        mock_select_candidates.return_value = [
            candidate_hash
        ]
        promoted_pair = self.promoter.promote_label_to_label(
            'tripleo-ci-testing', 'tripleo-ci-staging-promoted')
        mock_log_warning.assert_has_calls([
            mock.call("Candidate hash '%s': NO successful jobs",
                      candidate_hash),
        ])
        self.assertFalse(mock_promote.called)
        self.assertFalse(mock_log_error.called)
        self.assertEqual(promoted_pair, ())

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('logging.Logger.warning')
    @patch('logic.Promoter.select_candidates')
    @patch('logic.Promoter.promote')
    @patch('dlrn_client.DlrnClient.fetch_jobs')
    def test_promote_label_to_label_no_candidates(self,
                                                  mock_fetch_jobs,
                                                  mock_promote,
                                                  mock_select_candidates,
                                                  mock_log_warning,
                                                  mock_log_info,
                                                  mock_log_error):
        mock_select_candidates.return_value = []
        promoted_pair = self.promoter.promote_label_to_label(
            'tripleo-ci-testing', 'tripleo-ci-staging-promoted')
        mock_log_warning.assert_has_calls([
            mock.call("Candidate label '%s': No candidate hashes",
                      'tripleo-ci-testing')
        ])
        self.assertFalse(mock_fetch_jobs.called)
        self.assertFalse(mock_promote.called)
        self.assertFalse(mock_log_info.called)
        self.assertFalse(mock_log_error.called)
        self.assertEqual(promoted_pair, ())

    @patch('logging.Logger.debug')
    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('logging.Logger.warning')
    @patch('logic.Promoter.select_candidates')
    @patch('logic.Promoter.promote')
    @patch('dlrn_client.DlrnClient.fetch_jobs')
    @patch('dlrn_client.DlrnClient.get_civotes_info')
    def test_promote_label_to_label_success(self,
                                            mock_civotes,
                                            mock_fetch_jobs,
                                            mock_promote,
                                            mock_select_candidates,
                                            mock_log_warning,
                                            mock_log_info,
                                            mock_log_error,
                                            mock_log_debug):
        ci_votes = "http://host.to/detailspage.html"
        candidate_hashes = [
            DlrnCommitDistroExtendedHash(commit_hash='a', distro_hash='b'),
            DlrnCommitDistroExtendedHash(commit_hash='c', distro_hash='c')
        ]
        required_set = {
            'staging-job-1',
            'staging-job-2'
        }
        pair = (candidate_hashes[0], 'tripleo-ci-staging-promoted')
        mock_promote.return_value = pair
        mock_civotes.return_value = ci_votes
        mock_select_candidates.return_value = candidate_hashes
        mock_fetch_jobs.return_value = list(required_set)
        promoted_pair = self.promoter.promote_label_to_label(
            'tripleo-ci-testing', 'tripleo-ci-staging-promoted')

        mock_log_info.assert_has_calls([
            mock.call("Candidate label '%s': %d candidates",
                      'tripleo-ci-testing', 2),
            mock.call("Candidate label '%s': Checking candidates that meet "
                      "promotion criteria for target label '%s'",
                      'tripleo-ci-testing', 'tripleo-ci-staging-promoted'),
            mock.call("Candidate hash '%s': vote details page - %s",
                      candidate_hashes[0], ci_votes),
            mock.call("Candidate hash '%s': criteria met, attempting promotion "
                      "to %s", candidate_hashes[0],
                      'tripleo-ci-staging-promoted'),
        ])
        self.assertFalse(mock_log_warning.called)
        self.assertFalse(mock_log_error.called)
        self.assertEqual(promoted_pair, pair)
        # Ensure that we stop at the first promotion
        self.assertEqual(mock_promote.call_count, 1)

    @patch('logging.Logger.error')
    @patch('logging.Logger.warning')
    @patch('logic.Promoter.select_candidates')
    @patch('logic.Promoter.promote')
    @patch('dlrn_client.DlrnClient.fetch_jobs')
    @patch('dlrn_client.DlrnClient.get_civotes_info')
    def test_promote_label_to_label_empty_promoted_pair(
            self,
            mock_civotes,
            mock_fetch_jobs,
            mock_promote,
            mock_select_candidates,
            mock_log_warning,
            mock_log_error):
        ci_votes = "http://host.to/detailspage.html"
        candidate_hashes = [
            DlrnCommitDistroExtendedHash(commit_hash='a', distro_hash='b'),
            DlrnCommitDistroExtendedHash(commit_hash='c', distro_hash='c')
        ]
        required_set = {
            'staging-job-1',
            'staging-job-2'
        }
        mock_promote.side_effect = [(), ()]
        mock_civotes.return_value = ci_votes
        mock_select_candidates.return_value = candidate_hashes
        mock_fetch_jobs.return_value = list(required_set)
        promoted_pair = self.promoter.promote_label_to_label(
            'tripleo-ci-testing', 'tripleo-ci-staging-promoted')

        self.assertFalse(mock_log_warning.called)
        self.assertFalse(mock_log_error.called)
        # Ensure that we try two promotions
        self.assertEqual(mock_promote.call_count, 2)
        self.assertEqual(promoted_pair, ())


class TestPromoteAll(ConfigSetup):

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
                      'tripleo-ci-staging', 'tripleo-ci-staging-promoted'),
            mock.call("Summary: Promoted 1 hashes this round"),
            mock.call('------- -------- Promoter terminated normally')
        ])
        mock_promote_label_to_label.assert_has_calls([
            mock.call('tripleo-ci-staging', 'tripleo-ci-staging-promoted')
        ])
        self.assertEqual(promoted_pairs, [('label', 'hash')])

    @patch('dlrnapi_client.DefaultApi.api_promotions_get')
    @patch('logging.Logger.info')
    @patch('logging.Logger.warning')
    @patch('logging.Logger.error')
    @patch('logic.Promoter.promote_label_to_label')
    def test_promote_all_failure(self, mock_promote_label_to_label,
                                 mock_log_error,
                                 mock_log_warning,
                                 mock_log_info,
                                 mock_dlrn_api_promotions):
        mock_promote_label_to_label.side_effect = PromotionError
        promoted_pairs = self.promoter.promote_all()
        mock_log_error.assert_has_calls([
            mock.call("Error while trying to promote %s to %s",
                      'tripleo-ci-staging', 'tripleo-ci-staging-promoted')
        ])
        mock_log_warning.assert_has_calls([
            mock.call("Candidate label '%s': NO candidate "
                      "hash promoted to %s", 'tripleo-ci-staging',
                      'tripleo-ci-staging-promoted')
        ])
        self.assertTrue(mock_dlrn_api_promotions.called)
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
            mock.call('candidate_label', count='10'),
        ])

        assert (len(obtained_hashes) == 0)

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
        assert (len(obtained_hashes) == 0)
        fetch_hashes_mock.assert_has_calls([
            mock.call('candidate_label', count='10'),
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
            mock.call('candidate_label', count='10'),
            mock.call('target_label')
        ])

        assert (obtained_hashes == candidate_hashes)

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
            mock.call('candidate_label', count='10'),
            mock.call('target_label')
        ])

        assert (obtained_hashes == expected_hashes)
