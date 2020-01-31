import unittest

import pytest


class TestCommon(unittest.TestCase):

    @pytest.mark.xfail(reason="Not implemented")
    def test_check_port_defaults(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_check_port_open_true(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_check_port_open_false(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_check_port_open_timeout(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_check_port_closed_timeout(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_check_port_closed_true(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_check_port_closed_false(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_str2bool_true(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_str2bool_false(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_str2bool_whatever(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_setup_logging_no_handlers(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_setup_logging_wrong_log_file(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_setup_logging_corrent_log_file(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_close_logging(self):
        assert False