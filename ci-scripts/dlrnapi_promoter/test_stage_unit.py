import pytest
import unittest

from stage import parse_args, StageConfig


class TestMain(unittest.TestCase):

    def test_parse_args(self):
        line = ("--scenes dlrn,registries --dry-run --promoter-user prom"
                " --stage-config-file config.yaml --db-data-file fix.yaml"
                " setup")
        args = parse_args(cmd_line=line)
        assert args.action == "setup"
        assert args.dry_run is True
        assert args.promoter_user == "prom"
        assert args.db_data_file == 'fix.yaml'
        assert args.stage_config_file == 'config.yaml'
        assert args.scenes == ['dlrn', 'registries']
        line = "teardown"
        args = parse_args(cmd_line=line)
        assert args.action == "teardown"
        assert args.dry_run is False
        assert args.promoter_user == StageConfig.defaults.promoter_user
        assert args.db_data_file == StageConfig.defaults.db_data_file
        assert args.stage_config_file == StageConfig.defaults.stage_config_file
        assert args.scenes == StageConfig.defaults.scenes
        line = "--scenes dlrn"
        with self.assertRaises(SystemExit):
            parse_args(cmd_line=line)

    @pytest.mark.xfail(reason="Not implemented")
    def test_main_setup(self):
        assert False

    @pytest.mark.xfail(reason="Not implemented")
    def test_main_teardown(self):
        assert False


class TestContainersStage(unittest.TestCase):

    @pytest.mark.xfail(reason="Not implemented")
    def test_containers_yaml(self):
        assert False
