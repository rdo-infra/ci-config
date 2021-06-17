import os
import shutil
import unittest

from promoter.common import LockError
from promoter.dlrn_hash import DlrnCommitDistroExtendedHash

try:
    # Python3 imports
    from unittest import mock
    from unittest.mock import patch
except ImportError:
    # Python2 imports
    from mock import patch
    import mock

from promoter.dlrnapi_promoter import arg_parser, force_promote
from promoter.dlrnapi_promoter import main as promoter_main
from promoter.dlrnapi_promoter import promote_all
from promoter.logic import Promoter

log_dir = "~/web/promoter_logs"


class TestMain(unittest.TestCase):
    def setUp(self):
        log_d = os.path.expanduser(log_dir)
        if not os.path.isdir(log_d):
            os.makedirs(log_d)

    def tearDown(self):
        try:
            shutil.rmtree(os.path.expanduser(log_dir))
        except Exception:
            pass

    def test_arg_parser_defaults_promote_all(self):
        cmd_line = "--config-root rdo --release-config \
                    CentOS-8/master.yaml promote-all"
        args = arg_parser(cmd_line)
        self.assertEqual(args.config_root, "rdo")
        self.assertEqual(args.release_config, "CentOS-8/master.yaml")
        self.assertEqual(args.log_level, "INFO")
        self.assertEqual(args.handler, promote_all)

    def test_arg_parser_defaults_force_promote(self):
        cmd_line = ("--release-config CentOS-8/master.yaml force-promote "
                    "--commit-hash a "
                    "--distro-hash b "
                    "src dst")
        args = arg_parser(cmd_line)
        self.assertEqual(args.allowed_clients, 'registries_client,qcow_client,'
                                               'dlrn_client')
        self.assertEqual(args.handler, force_promote)

    def test_main_missing_config_file(self):
        with self.assertRaises(FileNotFoundError):
            promoter_main(cmd_line="--release-config Ubuntu/master.yaml"
                                   " promote-all")

    @mock.patch.object(Promoter, '__init__', autospec=True, return_value=None)
    @patch('promoter.common.get_lock')
    def test_main_lock_fail(self, get_lock_mock, init_mock):
        get_lock_mock.side_effect = LockError
        with self.assertRaises(LockError):
            promoter_main(cmd_line="--release-config CentOS-8/master.yaml"
                                   " promote-all")

        self.assertFalse(init_mock.called)


class TestPromoteAll(unittest.TestCase):
    def setUp(self):
        log_d = os.path.expanduser(log_dir)
        if not os.path.isdir(log_d):
            os.makedirs(log_d)

    def tearDown(self):
        try:
            shutil.rmtree(os.path.expanduser(log_dir))
        except Exception:
            pass

    @mock.patch.object(Promoter, '__init__', autospec=True, return_value=None)
    @mock.patch.object(Promoter, 'promote_all', autospec=True)
    def test_promote_all(self, start_process_mock, init_mock):

        promoter_main(cmd_line="--release-config CentOS-8/master.yaml"
                               " promote-all")

        assert init_mock.called
        assert start_process_mock.called


class TestForcePromote(unittest.TestCase):
    def setUp(self):
        log_d = os.path.expanduser(log_dir)
        if not os.path.isdir(log_d):
            os.makedirs(log_d)

    def tearDown(self):
        try:
            shutil.rmtree(os.path.expanduser(log_dir))
        except Exception:
            pass

    @mock.patch.object(Promoter, '__init__', autospec=True, return_value=None)
    @mock.patch.object(Promoter, 'promote_all', autospec=True)
    @mock.patch.object(Promoter, 'promote', autospec=True)
    def test_force_promote_missing_target_label(self,
                                                single_promote_mock,
                                                start_process_mock,
                                                init_mock):

        cmd_line = ("--relase-config CentOS-8/master.yaml force-promote "
                    "--commit-hash a "
                    "--distro-hash b "
                    "--aggregate-hash c "
                    "tripleo-ci-testing")
        with self.assertRaises(SystemExit):
            promoter_main(cmd_line=cmd_line)

        self.assertFalse(init_mock.called)
        self.assertFalse(start_process_mock.called)

    @mock.patch.object(Promoter, '__init__', autospec=True, return_value=None)
    @mock.patch.object(Promoter, 'promote_all', autospec=True)
    @mock.patch.object(Promoter, 'promote', autospec=True)
    def test_force_promote_missing_candidate_label(self,
                                                   single_promote_mock,
                                                   start_process_mock,
                                                   init_mock):

        cmd_line = ("--release-config CentOS-8/master.yaml force-promote "
                    "--commit-hash a "
                    "--distro-hash b "
                    "--aggregate-hash c ")

        with self.assertRaises(SystemExit):
            promoter_main(cmd_line=cmd_line)

        self.assertFalse(init_mock.called)
        self.assertFalse(start_process_mock.called)
        self.assertFalse(single_promote_mock.called)

    @mock.patch.object(Promoter, '__init__', autospec=True, return_value=None)
    @mock.patch.object(Promoter, 'promote_all', autospec=True)
    @mock.patch.object(Promoter, 'promote', autospec=True)
    def test_force_promote_success(self,
                                   single_promote_mock,
                                   start_process_mock,
                                   init_mock):

        candidate_hash = DlrnCommitDistroExtendedHash(
            commit_hash="a", distro_hash="b")
        cmd_line = ("--release-config CentOS-8/master.yaml force-promote "
                    "--commit-hash a "
                    "--distro-hash b "
                    "tripleo-ci-staging "
                    "current-tripleo")
        promoter_main(cmd_line=cmd_line)

        self.assertTrue(init_mock.called)
        self.assertFalse(start_process_mock.called)
        single_promote_mock.assert_has_calls([
            mock.call(mock.ANY, candidate_hash, 'tripleo-ci-staging',
                      'current-tripleo')
        ])
