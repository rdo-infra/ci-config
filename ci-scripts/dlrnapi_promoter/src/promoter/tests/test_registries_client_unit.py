import subprocess

import yaml

try:
    # Python3 imports
    from unittest import mock
    from unittest.mock import patch
except ImportError:
    # Python2 imports
    from mock import patch
    import mock

from promoter.common import PromotionError
from promoter.dlrn_hash import DlrnCommitDistroExtendedHash, DlrnHash

from .test_unit_fixtures import ConfigSetup, hashes_test_cases


class TestPrepareExtraVars(ConfigSetup):

    maxDiff = None

    def setUp(self):
        super(TestPrepareExtraVars, self).setUp()
        self.client = self.promoter.registries_client
        self.dlrn_hash_commitdistro = DlrnCommitDistroExtendedHash(
            commit_hash='abc', distro_hash='def', component="comp1",
            timestamp=1)

    def test_setup(self):
        error_msg = "Container push logfile is misplaced"
        assert self.client.logfile != "", error_msg

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('logging.Logger.debug')
    @patch('promoter.repo_client.RepoClient.get_versions_csv')
    @patch('promoter.repo_client.RepoClient.get_commit_sha')
    @patch('promoter.repo_client.RepoClient.get_containers_list')
    def test_prepare_extra_vars_empty_missing_reader(self,
                                                     get_containers_mock,
                                                     get_commit_mock,
                                                     get_versions_mock,
                                                     mock_log_debug,
                                                     mock_log_info,
                                                     mock_log_error):

        get_versions_mock.return_value = None
        with self.assertRaises(PromotionError):
            self.client.prepare_extra_vars(self.dlrn_hash_commitdistro,
                                           "current-tripleo",
                                           "tripleo-ci-testing")
        get_versions_mock.assert_has_calls([
            mock.call(self.dlrn_hash_commitdistro, "tripleo-ci-testing")
        ])
        self.assertFalse(get_commit_mock.called)
        self.assertFalse(get_containers_mock.called)
        self.assertFalse(mock_log_debug.called)
        self.assertFalse(mock_log_info.called)
        mock_log_error.assert_has_calls([
            mock.call("No versions.csv found")
        ])

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('logging.Logger.debug')
    @patch('promoter.repo_client.RepoClient.get_versions_csv')
    @patch('promoter.repo_client.RepoClient.get_commit_sha')
    @patch('promoter.repo_client.RepoClient.get_containers_list')
    def test_prepare_extra_vars_empty_missing_sha(self,
                                                  get_containers_mock,
                                                  get_commit_mock,
                                                  get_versions_mock,
                                                  mock_log_debug,
                                                  mock_log_info,
                                                  mock_log_error):

        get_versions_mock.return_value = "reader"
        get_commit_mock.return_value = None
        with self.assertRaises(PromotionError):
            self.client.prepare_extra_vars(self.dlrn_hash_commitdistro,
                                           "current-tripleo",
                                           "tripleo-ci-testing")
        get_versions_mock.assert_has_calls([
            mock.call(self.dlrn_hash_commitdistro, "tripleo-ci-testing")
        ])
        get_commit_mock.assert_has_calls([
            mock.call("reader", "openstack-tripleo-common")
        ])
        self.assertFalse(get_containers_mock.called)
        self.assertFalse(mock_log_debug.called)
        self.assertFalse(mock_log_info.called)
        mock_log_error.assert_has_calls([
            mock.call("Versions.csv does not contain tripleo-common commit")
        ])

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('logging.Logger.debug')
    @patch('promoter.repo_client.RepoClient.get_versions_csv')
    @patch('promoter.repo_client.RepoClient.get_commit_sha')
    @patch('promoter.repo_client.RepoClient.get_containers_list')
    def test_prepare_extra_vars_empty_containers_list(self,
                                                      get_containers_mock,
                                                      get_commit_mock,
                                                      get_versions_mock,
                                                      mock_log_debug,
                                                      mock_log_info,
                                                      mock_log_error):

        get_versions_mock.return_value = "reader"
        get_commit_mock.return_value = "abc"
        get_containers_mock.return_value = {'containers_list': []}
        with self.assertRaises(PromotionError):
            self.client.prepare_extra_vars(self.dlrn_hash_commitdistro,
                                           "current-tripleo",
                                           "tripleo-ci-testing")
        get_versions_mock.assert_has_calls([
            mock.call(self.dlrn_hash_commitdistro, "tripleo-ci-testing")
        ])
        get_commit_mock.assert_has_calls([
            mock.call("reader", "openstack-tripleo-common")
        ])
        get_containers_mock.assert_has_calls([
            mock.call("abc")
        ])
        self.assertFalse(mock_log_debug.called)
        self.assertFalse(mock_log_info.called)
        mock_log_error.assert_has_calls([
            mock.call("Containers list is empty")
        ])

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('logging.Logger.debug')
    @patch('promoter.repo_client.RepoClient.get_versions_csv')
    @patch('promoter.repo_client.RepoClient.get_commit_sha')
    @patch('promoter.repo_client.RepoClient.get_containers_list')
    def test_prepare_extra_vars_success(self,
                                        get_containers_mock,
                                        get_commit_mock,
                                        get_versions_mock,
                                        mock_log_debug,
                                        mock_log_info,
                                        mock_log_error):

        get_versions_mock.return_value = "reader"
        get_commit_mock.return_value = "abc"
        get_containers_mock.return_value = {'containers_list': ['a', 'b']}
        extra_vars_path = \
            self.client.prepare_extra_vars(self.dlrn_hash_commitdistro,
                                           "current-tripleo",
                                           "tripleo-ci-testing")
        self.assertIsInstance(extra_vars_path, str)
        self.assertIn(".yaml", extra_vars_path)
        with open(extra_vars_path) as extra_vars_file:
            extra_vars = yaml.safe_load(stream=extra_vars_file)
        self.assertIsInstance(extra_vars, dict)
        self.assertDictEqual(extra_vars, {
            'release': "master",
            'script_root': mock.ANY,
            'distro_name': "centos",
            'distro_version': 8,
            'manifest_push': 'true',
            'target_registries_push': 'true',
            'candidate_label': "tripleo-ci-testing",
            "named_label": "current-tripleo",
            'ppc_containers_list': [],
            "source_namespace": "tripleomaster",
            "target_namespace": "tripleomaster",
            "commit_hash": self.dlrn_hash_commitdistro.commit_hash,
            "distro_hash": self.dlrn_hash_commitdistro.distro_hash,
            "full_hash": self.dlrn_hash_commitdistro.full_hash,
            "containers_list": ['a', 'b']
        })
        get_versions_mock.assert_has_calls([
            mock.call(self.dlrn_hash_commitdistro, "tripleo-ci-testing")
        ])
        get_commit_mock.assert_has_calls([
            mock.call("reader", "openstack-tripleo-common")
        ])
        get_containers_mock.assert_has_calls([
            mock.call("abc")
        ])
        mock_log_debug.assert_has_calls([
            mock.call("Crated extra vars file at %s", mock.ANY)
        ])
        mock_log_info.assert_has_calls([
            mock.call("Passing extra vars to playbook: %s", mock.ANY)
        ])
        self.assertFalse(mock_log_error.called)


class TestPromote(ConfigSetup):

    def setUp(self):
        super(TestPromote, self).setUp()
        self.client = self.promoter.registries_client
        self.dlrn_hash_commitdistro = DlrnCommitDistroExtendedHash(
            commit_hash='abc',
            distro_hash='def',
            component="comp1",
            timestamp=1)

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('os.unlink')
    @patch('promoter.registries_client.RegistriesClient.prepare_extra_vars')
    @mock.patch('subprocess.check_output')
    def test_promote_success(self, check_output_mock,
                             extra_vars_mock,
                             unlink_mock,
                             mock_log_info,
                             mock_log_error
                             ):
        candidate_hash =\
            DlrnHash(source=hashes_test_cases['aggregate']['dict']['valid'])
        target_label = "test"

        check_output_mock.return_value = "test log"
        self.client.promote(candidate_hash, target_label)

        self.assertTrue(check_output_mock.called)
        self.assertFalse(mock_log_error.called)

    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    @patch('os.unlink')
    @patch('promoter.registries_client.RegistriesClient.prepare_extra_vars')
    @mock.patch('subprocess.check_output')
    def test_promote_failure(self, check_output_mock,
                             extra_vars_mock,
                             unlink_mock,
                             mock_log_info,
                             mock_log_error
                             ):
        candidate_hash = \
            DlrnHash(source=hashes_test_cases['aggregate']['dict']['valid'])
        target_label = "test"
        exception = subprocess.CalledProcessError(1, 2)
        exception.output = b"test"
        check_output_mock.side_effect = exception
        with self.assertRaises(PromotionError):
            self.client.promote(candidate_hash, target_label)
        self.assertTrue(mock_log_error.called)
