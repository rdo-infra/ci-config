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
        'fixture_file': "scenario-1.yaml",
        "stage-config-file": "stage-config-secure.yaml"
    }
    stage_config = load_config(overrides)
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
            "api_url": stage_info['dlrn']['api_url'],
            "dlrn_repo_url": stage_info['dlrn']['repo_url'],
            "dlrn_username": stage_info['dlrn']['username'],
            "dlrn_password": stage_info['dlrn']['password'],
            "openstack_repo_url": stage_info['containers_yaml_url'],
            "registries": stage_info['registries']
        }
    }

    promoter_config = PromoterConfig(config)

    yield promoter_config, stage_info

    #staged_env.teardown()

class ApiResponse(object):
    pass

def test_promote_agent_validate_hash(staged_env):

    promoter_config, stage_info = staged_env
    # We have promotions in the fixtures for this,
    # no need to use dlrnapi to promote
    pa = PromoterAgent(promoter_config)
    commit = stage_info['commits'][0]
    target_hash = DlrnHash(commit=commit['commit_hash'], distro=commit['distro_hash'])
    target_name = commit['name']
    results = pa.dlrn_client.validate_hash(target_hash, target_name)
    assert results['hash_exists'] == True, "verify_link says hash doesn't exist, but it does"
    assert results['name_points_hash'] == True, "verify_link says name does not point to hash, but it does"

    target_hash = DlrnHash(commit=commit['commit_hash'], distro=commit['distro_hash'])
    target_name = "notexisting"
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

def test_no_rollback_needed(staged_env):

    promoter_config, stage_info = staged_env

    attempted_commit = stage_info['commits'][0]
    rollback_commit = stage_info['commits'][1]

    attempted_hash = DlrnHash(commit=attempted_commit['commit_hash'],
                              distro=attempted_commit['distro_hash'])
    rollback_hash = DlrnHash(commit=rollback_commit['commit_hash'],
                              distro=rollback_commit['distro_hash'])

    # Set the target name to whatever promotion name attempted has already has
    target_name = attempted_commit['name']

    # Suppose everything was running ok
    pa = PromoterAgent(promoter_config)
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
