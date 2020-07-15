import unittest

import pytest


class TestQcowStagingServer(unittest.TestCase):

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_create_hierarchy_dir_exist(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_create_hierarchy_success(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_teardown_success(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_teardown_no_dir(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_stage_info(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_promote_overcloud_images_success(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_promote_overcloud_images_link_exist(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_setup_dir_exist(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_setup_success(self):
        assert False
