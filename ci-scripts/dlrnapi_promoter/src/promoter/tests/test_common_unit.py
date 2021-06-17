import datetime
import logging
import os
import subprocess
import tempfile
import unittest

import dlrnapi_client
import pytest
from promoter.common import (LoggingError, check_port, close_logging, get_lock,
                             get_log_file, get_root_paths, setup_logging,
                             str_api_object)

try:
    # Python3 imports
    from unittest import mock
    from unittest.mock import patch
except ImportError:
    # Python2 imports
    import mock
    from mock import patch

try:
    # In python 2 ConnectionRefusedError is not a builtin
    from socket import error as ConnectionRefusedError  # noqa: N812
except ImportError:
    pass


class TestCheckPort(unittest.TestCase):

    @patch('socket.socket.connect')
    def test_check_port_open_true(self, socket_connect_mock):
        socket_connect_mock.return_value = True
        self.assertTrue(check_port("localhost", 100))

    @patch('socket.socket.connect')
    def test_check_port_open_timeout(self, socket_connect_mock):
        socket_connect_mock.side_effect = ConnectionRefusedError
        timestamp_start = datetime.datetime.now()
        self.assertFalse(check_port("localhost", 100, timeout=2))
        timestamp_end = datetime.datetime.now()
        timedelta_check = \
            timestamp_end - timestamp_start >= datetime.timedelta(seconds=2)
        error_msg = "Timeout not honored"
        assert timedelta_check, error_msg

    @patch('socket.socket.connect')
    def test_check_port_closed_timeout(self, socket_connect_mock):
        socket_connect_mock.return_value = True
        timestamp_start = datetime.datetime.now()
        self.assertFalse(check_port("localhost", 100,
                                    timeout=2,
                                    port_mode="closed"))
        timestamp_end = datetime.datetime.now()
        timedelta_check = \
            timestamp_end - timestamp_start >= datetime.timedelta(seconds=2)
        error_msg = "Timeout not honored"
        self.assertTrue(timedelta_check, error_msg)

    @patch('socket.socket.connect')
    def test_check_port_closed_true(self, socket_connect_mock):
        socket_connect_mock.side_effect = ConnectionRefusedError
        self.assertTrue(check_port("localhost", 100, port_mode="closed"))


class TestLogging(unittest.TestCase):

    @patch('logging.Logger.info')
    def test_setup_logging_no_handlers(self, mock_log_info):
        setup_logging("tests", logging.DEBUG)
        self.assertFalse(mock_log_info.called)

    def test_setup_logging_wrong_log_file(self):
        with pytest.raises(LoggingError):
            setup_logging("tests", logging.DEBUG, log_file="/does/not/exist")

    @patch('logging.Logger.info')
    def test_setup_logging_correct_log_file(self, mock_log_info):
        __, filepath = tempfile.mkstemp()
        setup_logging("tests", logging.DEBUG, log_file=filepath)
        os.unlink(filepath)
        mock_log_info.assert_has_calls([
            mock.call('Set up logging level %%s on:  file %s' % filepath,
                      'DEBUG')
        ])

    def test_close_logging(self):
        __, filepath = tempfile.mkstemp()
        setup_logging("test", logging.DEBUG, log_file=filepath)
        logger = logging.getLogger("test")
        self.assertGreater(len(logger.handlers), 0)
        close_logging("test")
        self.assertEqual(len(logger.handlers), 0)
        os.unlink(filepath)


class TestStrApiObject(unittest.TestCase):

    def test_str_api_object(self):
        params = dlrnapi_client.PromotionQuery()
        str_params = str_api_object(params)
        self.assertNotIn("\n", str(str_params))


class TestGetRootPaths(unittest.TestCase):

    @patch('logging.Logger.error')
    @patch('subprocess.check_output')
    def test_get_root_paths_success(self, check_output_mock,
                                    mock_log_error):
        check_output_mock.return_value = "/path/to/some/root"
        repo_root, code_root = get_root_paths()
        self.assertEqual(repo_root, "/path/to/some/root")
        self.assertEqual(code_root,
                         "/path/to/some/root/ci-scripts/dlrnapi_promoter")
        self.assertFalse(mock_log_error.called)

    @patch('logging.Logger.error')
    @patch('os.path.abspath')
    @patch('os.chdir')
    @patch('subprocess.check_output')
    def test_get_root_paths_failure(self, check_output_mock,
                                    chdir_mock,
                                    abspath_mock,
                                    mock_log_error):
        exception = subprocess.CalledProcessError(1, 2)
        check_output_mock.side_effect = exception
        abspath_mock.return_value = "/path/to/orig_root"
        repo_root, code_root = get_root_paths()
        mock_log_error.assert_has_calls([
            mock.call("Unable to get git root dir, using %s",
                      "/path/to/orig_root")
        ])
        self.assertEqual(repo_root, "/path/to/orig_root")
        self.assertEqual(code_root,
                         "/path/to/orig_root/ci-scripts/dlrnapi_promoter")


class TestGeLock(unittest.TestCase):

    def test_get_lock(self):
        repo_root, code_root = get_root_paths()
        os.chdir(code_root)
        get_lock('test')
        # We need a different process trying to access the same lock and fail
        with self.assertRaises(subprocess.CalledProcessError) as ex:
            subprocess.check_output(['python', '-c',
                                     'from promoter.common import get_lock;'
                                     'get_lock("test")'],
                                    stderr=subprocess.STDOUT)
        self.assertIn("Another promoter process is running.",
                      ex.exception.output.decode())


class TestGetLogFile(unittest.TestCase):
    def test_get_log_file(self):
        log_file = get_log_file("staging", "CentOS-8/master.yaml")
        assert mock.ANY == log_file

    def test_get_log_file_invalid_file(self):
        with self.assertRaises(FileNotFoundError):
            get_log_file("staging", "Ubuntu/master.yaml")
