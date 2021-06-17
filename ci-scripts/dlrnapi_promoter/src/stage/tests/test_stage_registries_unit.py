import unittest

import pytest


class TestLocalRegistry(unittest.TestCase):

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_get_base_image_exists(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_get_base_image_download(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_get_secure_base_image_exists(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_get_secure_base_image_build(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_build_secure_base_image_download(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_is_running_false(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_is_running_true(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_run_already_running(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_run_success(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_run_failure(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_run_secure(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_stop_success(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_stop_not_running(self):
        assert False


class TestStagingRegistries(unittest.TestCase):

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_target_registry(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_source_registry(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_stage_info(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_setup_success(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_teardown(self):
        assert False
