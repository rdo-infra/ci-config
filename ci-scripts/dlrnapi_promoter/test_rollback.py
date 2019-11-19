import dlrnapi_client
import pytest
import os
import yaml

try:
    import configparser as ini_parser
except ImportError:
    import ConfigParser as ini_parser


try:
    from unittest.mock import patch
except ImportError:
    from mock import patch, mock
from tests.staging_setup.staging_environment import load_config, StagedEnvironment
from agent import PromoterAgent
from common import DlrnHash, PromoterConfig


@pytest.fixture(scope='function')
def promoterconfig():
    """
    Fixture that runs the staging environment provisioner, yields the files
    produced and cleans up after
    """

    overrides = {
        'components': "all",
        'stage-info-path': "/tmp/stage-info.yaml",
        'dry-run': False,
        'promoter_user': "centos",
        'fixture_file': "scenario-1.yaml"
    }
    stage_config = load_config(overrides, db_filepath="/tmp/sqlite-test.db")
    staged_env = StagedEnvironment(stage_config)
    staged_env.setup()
    with open(stage_config['stage-info-path'], "r") as stage_info_path:
        stage_info = yaml.safe_load(stage_info_path)

    config = {
        'main': {
            'distro_name': "centos",
            "distro_version": "7",
            "release": "master",
            "dry_run": "false",
            "api_url": stage_info['dlrn_host'],
            "dlrn_repo_scheme": "file",
            "dlrn_repo_host": "",
            "dlrn_repo_root": s + "tmp/data/repos",
        }
    }
    promoter_config = PromoterConfig(config)

    yield promoter_config

    staged_env.teardown()

# TODO(gcerami): Too much mocking for the functional tests
# Move this mocking to unit tests, make stage env
# handle real dlrnapi server and test the real interaction here

@pytest.fixture(autouse=True)
def dlrn_offline(monkeypatch):
    def mock_api_promotions_get(_, promotion_name):
        ar = ApiResponse()
        setattr(ar, "commit_hash", "a")
        setattr(ar, "distro_hash", "a")
        setattr(ar, "promotion_name", "b")
        return [ar]
    def mock_api_repo_status_get(_, dlrn_hash):
        return []
    def mock_api_promote_post(_, params):
        return
    monkeypatch.setattr(dlrnapi_client.apis.default_api.DefaultApi,
                        "api_promotions_get", mock_api_promotions_get)
    monkeypatch.setattr(dlrnapi_client.apis.default_api.DefaultApi,
                        "api_repo_status_get", mock_api_repo_status_get)
    monkeypatch.setattr(dlrnapi_client.apis.default_api.DefaultApi,
                        "api_promote_post", mock_api_promote_post)

class ApiResponse(object):
    pass

def test_promote_agent_validate_hash(promoterconfig):
    # We have promotions in the fixtures for this,
    # no need to use dlrnapi to promote
    pa = PromoterAgent(config)
    target_hash = ApiResponse()
    setattr(target_hash, "commit_hash", "a")
    setattr(target_hash, "distro_hash", "a")
    target_name = "b"
    results = pa.dlrn_client.validate_hash(target_hash, target_name)
    assert results['hash_exists'] == True, "verify_link says hash doesn't exist, but it does"
    assert results['name_points_hash'] == True, "verify_link says name does not point to hash, but it does"

    target_hash = ApiResponse()
    setattr(target_hash, "commit_hash", "b")
    setattr(target_hash, "distro_hash", "b")
    target_name = "b"
    results = pa.dlrn_client.validate_hash(target_hash, target_name)
    assert results['name_points_hash'] == False, "verify_link says name does point to hash, but it doesn't"

def test_promote_agent_promote_link(staged_env, config):
    target_hash = ApiResponse()
    setattr(target_hash, "commit_hash", "a")
    setattr(target_hash, "distro_hash", "a")

    candidate_hash = "a"
    target_name = "b"
    pa = PromoterAgent(config)
    pa.promote_link(candidate_hash, target_name)
    # verify

def test_no_rollback_needed(promoterconfig):

    attempted_hash = ApiResponse()
    setattr(attempted_hash, "commit_hash", "b")
    setattr(attempted_hash, "distro_hash", "b")

    rollback_hash = DlrnHash(commit="a", distro="b")

    target_name = "b"

    # Suppose everything was running ok
    pa = PromoterAgent(promoterconfig)
    transaction = pa.start_transaction(attempted_hash, rollback_hash, target_name)
    transaction.checkpoint("containers", "start")
    transaction.checkpoint("containers", "end")
    transaction.checkpoint("qcow", "start")
    transaction.checkpoint("qcow", "end")

    # Imagine the hash was promoted, but transaction end was not called
    # Check we are not doing anything
    pa.dlrn_client.promote_hash(attempted_hash, target_name)
    transaction.rollback()

    pa.dlrn_hash.validate_hash(attempted_hash, target_name)

    # Check we are not doing anything after transaction end is called.
    pa.end_transaction()

    pa.transaction.rollback()
    pa.verify_link(candidate_hash, target_name)

def test_rollback_at_qcow():
    pass

def test_rollback_at_containers():
    pass

def test_rollback_everything():
    pass
