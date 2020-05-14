import pytest
import unittest

from common import LockError
from dlrn_hash import DlrnCommitDistroHash

try:
    # Python3 imports
    from unittest.mock import patch
    import unittest.mock as mock
except ImportError:
    # Python2 imports
    from mock import patch
    import mock

from dlrnapi_promoter import (main as promoter_main, arg_parser, promote_all,
                              force_promote)
from logic import Promoter


class TestMain(unittest.TestCase):

    def test_arg_parser_defaults_promote_all(self):
        cmd_line = "--config-file config.yaml promote-all"
        args = arg_parser(cmd_line)
        self.assertEqual(args.config_file, "config.yaml")
        self.assertEqual(args.log_level, "INFO")
        self.assertEqual(args.handler, promote_all)

    def test_arg_parser_defaults_force_promote(self):
        cmd_line = ("--config-file config.yaml force-promote "
                    "--commit-hash a "
                    "--distro-hash b "
                    "src dst")
        args = arg_parser(cmd_line)
        self.assertEqual(args.allowed_clients, 'registries_client,qcow_client,'
                                               'dlrn_client')
        self.assertEqual(args.handler, force_promote)

    def test_main_missing_config_file(self):
        with self.assertRaises(SystemExit):
            promoter_main(cmd_line="promote-all")

    @mock.patch.object(Promoter, '__init__', autospec=True, return_value=None)
    @patch('common.get_lock')
    def test_main_lock_fail(self, get_lock_mock, init_mock):
        get_lock_mock.side_effect = LockError
        with self.assertRaises(LockError):
            promoter_main(cmd_line="--config-file config.yaml promote-all")

        init_mock.assert_not_called()


class TestPromoteAll(unittest.TestCase):

    @mock.patch.object(Promoter, '__init__', autospec=True, return_value=None)
    @mock.patch.object(Promoter, 'promote_all', autospec=True)
    def test_promote_all(self, start_process_mock, init_mock):

        promoter_main(cmd_line="--config-file config.yaml promote-all")

        assert init_mock.called
        assert start_process_mock.called


class TestForcePromote(unittest.TestCase):

    @mock.patch.object(Promoter, '__init__', autospec=True, return_value=None)
    @mock.patch.object(Promoter, 'promote_all', autospec=True)
    @mock.patch.object(Promoter, 'promote', autospec=True)
    def test_force_promote_missing_target_label(self,
                                                single_promote_mock,
                                                start_process_mock,
                                                init_mock):

        cmd_line = ("--config-file config.yaml force-promote "
                    "--commit-hash a "
                    "--distro-hash b "
                    "--aggregate-hash c "
                    "tripleo-ci-testing")
        with self.assertRaises(SystemExit):
            promoter_main(cmd_line=cmd_line)

        init_mock.assert_not_called()
        start_process_mock.assert_not_called()

    @mock.patch.object(Promoter, '__init__', autospec=True, return_value=None)
    @mock.patch.object(Promoter, 'promote_all', autospec=True)
    @mock.patch.object(Promoter, 'promote', autospec=True)
    def test_force_promote_missing_candidate_label(self,
                                                   single_promote_mock,
                                                   start_process_mock,
                                                   init_mock):

        cmd_line = ("--config-file config.yaml force-promote "
                    "--commit-hash a "
                    "--distro-hash b "
                    "--aggregate-hash c ")

        with self.assertRaises(SystemExit):
            promoter_main(cmd_line=cmd_line)

        init_mock.assert_not_called()
        start_process_mock.assert_not_called()
        single_promote_mock.assert_not_called()

    @mock.patch.object(Promoter, '__init__', autospec=True, return_value=None)
    @mock.patch.object(Promoter, 'promote_all', autospec=True)
    @mock.patch.object(Promoter, 'promote', autospec=True)
    def test_force_promote_success(self,
                                   single_promote_mock,
                                   start_process_mock,
                                   init_mock):

        candidate_hash = DlrnCommitDistroHash(commit_hash="a", distro_hash="b")
        cmd_line = ("--config-file config.yaml force-promote "
                    "--commit-hash a "
                    "--distro-hash b "
                    "tripleo-ci-testing "
                    "current-tripleo")
        promoter_main(cmd_line=cmd_line)

        self.assertTrue(init_mock.called)
        start_process_mock.assert_not_called()
        single_promote_mock.assert_has_calls([
            mock.call(mock.ANY, candidate_hash, 'tripleo-ci-testing',
                      'current-tripleo')
        ])
