import pytest
import unittest

try:
    # Python3 imports
    from unittest.mock import patch
    import unittest.mock as mock
except ImportError:
    # Python2 imports
    from mock import patch
    import mock


from dlrnapi_promoter import main as promoter_main
from logic import Promoter


class TestMain(unittest.TestCase):

    @pytest.mark.xfail(reason="Not implemented")
    def test_arg_parser_correct(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_arg_parser_wrong_config_file(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_arg_parser_wrong_arg(self):
        assert False

    @mock.patch.object(Promoter, '__init__', autospec=True, return_value=None)
    @mock.patch.object(Promoter, 'promote_all', autospec=True)
    def test_main_call_new(self, start_process_mock, init_mock):

        promoter_main(cmd_line="config")

        assert init_mock.called
        assert start_process_mock.called
