import unittest

import pytest
from stage.stage_server import parse_args


class TestMain(unittest.TestCase):

    def setUp(self):
        self.line = ("--scenes dlrn,registries --dry-run --promoter-user prom"
                     " --db-data-file fix.yaml"
                     " setup --release-config release.yaml")
        self.defaults = {
            'scenes': '',
            'stage_info_file': '',
            'db_data_file': '',
        }

    def test_parse_args_setup(self):
        args = parse_args(self.defaults, cmd_line=self.line)
        assert 'setup' in args.handler.__repr__()
        assert args.dry_run is True
        assert args.promoter_user == "prom"
        assert args.db_data_file == 'fix.yaml'
        assert args.scenes.split(',') == ['dlrn', 'registries']

    def test_arg_parse_teardown(self):
        line = "teardown"
        args = parse_args(self.defaults, cmd_line=line)
        assert 'teardown' in args.handler.__repr__()
        assert args.dry_run is False
        assert args.db_data_file == ''
        assert args.scenes.split(',') == ['']

    def test_arg_parse_fail(self):
        line = "--scenes dlrn"
        with self.assertRaises(SystemExit):
            parse_args(self.defaults, cmd_line=line)

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_main_setup(self):
        assert False

    @pytest.mark.xfail(reason="Not Implemented", run=False)
    def test_main_teardown(self):
        assert False
