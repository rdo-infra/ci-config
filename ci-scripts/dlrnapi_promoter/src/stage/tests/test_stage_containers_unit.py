import unittest

import pytest


class TestBaseImage(unittest.TestCase):

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_build_exists(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_build(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_remove(self):
        assert False


class TestContainersStage(unittest.TestCase):

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_generate_containers_yaml(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_stage_info(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_cleanup_containers(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_teardown(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_setup(self):
        assert False
