import datetime
import logging
import os
import tempfile

import pytest
import unittest

from common import str2bool, check_port, setup_logging, LoggingError, \
    close_logging

try:
    # Python3 imports
    from unittest.mock import patch
    import unittest.mock as mock
except ImportError:
    # Python2 imports
    from mock import patch
    import mock

try:
    # In python 2 ConnectionRefusedError is not a builtin
    from socket import error as ConnectionRefusedError
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


class TestStr2Bool(unittest.TestCase):

    def test_str2bool_true(self):
        self.assertTrue(str2bool("yes"))
        self.assertTrue(str2bool("true"))
        self.assertTrue(str2bool("True"))
        self.assertTrue(str2bool("on"))
        self.assertTrue(str2bool("1"))

    def test_str2bool_false(self):
        self.assertFalse(str2bool("False"))
        self.assertFalse(str2bool(type("Whatever", (), {})))


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

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_str_api_object(self):
        assert False


class TestGetRootPaths(unittest.TestCase):

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_get_root_paths(self):
        assert False
