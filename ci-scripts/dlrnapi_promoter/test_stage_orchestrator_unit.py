import pytest
import unittest


class TestStageOrchestrator(unittest.TestCase):

    @pytest.mark.xfail(reason="Not implemented")
    def test_setup_success(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_setup_dir_exists(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_teardown_no_dir(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_teardown_success(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_stage_info(self):
        assert False
