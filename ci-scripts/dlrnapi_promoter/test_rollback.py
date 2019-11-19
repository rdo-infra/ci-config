import dlrnapi_client
import pytest
import os
import yaml

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch, mock
from tests.staging_setup.staging_environment import load_config, StagedEnvironment
from agent import PromoterAgent

@pytest.fixture(scope='function')
def staged_env():
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
    config = load_config(overrides, db_filepath="/tmp/sqlite-test.db")
    staged_env = StagedEnvironment(config)
    staged_env.setup()
    with open(config['stage-info-path'], "r") as stage_info_path:
        stage_info = yaml.safe_load(stage_info_path)

    yield config, stage_info

    staged_env.teardown()


@pytest.fixture(scope='function')
def config():
    config = {
        "dry_run": False,
        "distro": "centos",
        "release": "master",
        "api_url": "localhost:8080",
        "promote_name": "current_tripleo"
    }

    return config

# TODO(gcerami): Too muck mocking for the functional tests
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

def test_promote_agent_validate_hash(staged_env, config):
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


def test_no_rollback_needed(staged_env, config):

    attempted_hash = ApiResponse()
    setattr(attempted_hash, "commit_hash", "b")
    setattr(attempted_hash, "distro_hash", "b")

    rollback_hash = ApiResponse()
    setattr(rollback_hash, "commit_hash", "a")
    setattr(rollback_hash, "distro_hash", "a")

    target_name = "b"

    # Suppose everything was running ok
    pa = PromoterAgent(config)
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

