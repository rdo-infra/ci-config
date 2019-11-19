import dlrnapi_client
import pprint
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
from transaction import RollbackNotNeeded, RollbackError


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
        "stage-config-file": "stage-config-secure.yaml",
        "remove_local_containers": False,
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
            "registries": stage_info['registries'],
            "qcow_servers" : {
                "localhost": {
                    "host": "localhost",
                    "user": "unused",
                    "root": stage_info['overcloud_images']['base_dir']
                }
            },
            "qcow_server": "localhost"
        }
    }

    promoter_config = PromoterConfig(config)

    yield promoter_config, stage_info

    staged_env.teardown()

@pytest.fixture(scope='function')
def basic_setup(staged_env):

    class _basicvars(object):

        def __init__(self, rollback="rollback_hash"):

            promoter_config, stage_info = staged_env

            # Build hashes from dlrn db fixtures
            attempted_commit = stage_info['promotions']['promotion_candidate']
            rollback_commit = stage_info['promotions']['currently_promoted']

            attempted_hash = DlrnHash(from_dict=attempted_commit)
            rollback_hash = DlrnHash(from_dict=rollback_commit)
            invalid_hash = DlrnHash(commit="a", distro='a')

            # Set the target name to whatever promotion name attempted has
            # already an hash in the db
            target_name = attempted_commit['name']

            # Suppose everything was running ok up to dlrn promotion
            pa = PromoterAgent(promoter_config)

            # Set rollback hash base on parameter
            rollback_to = rollback_hash
            if rollback == "invalid_hash":
                rollback_to = invalid_hash

            # Push containers to target registry to simulate a partial pomotion
            pa.push_containers(stage_info['containers'], remove=True)
            transaction = pa.start_transaction(attempted_hash, rollback_to, target_name)
            transaction.checkpoint("containers", "start")
            transaction.checkpoint("containers", "end")
            transaction.checkpoint("qcows", "start")
            transaction.checkpoint("qcows", "end")

            # Roll back just dlrn link
            # FIXME(gcerami) this should not be needed, as the whole setup
            # is recreated for each test
            pa.dlrn_client.promote_hash(rollback_hash, target_name)

            self.attempted_hash = attempted_hash
            self.rollback_hash = rollback_hash
            self.invalid_hash = invalid_hash
            self.transaction = transaction
            self.pa = pa
            self.target_name = target_name

    def _basic_setup(*args, **kwargs):
        basic_vars = _basicvars(*args, **kwargs)

        return basic_vars

    yield _basic_setup


    # Cleanup containers

@pytest.mark.skip(reason="no completely valid hash avalable in staging yet")
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

@pytest.mark.skip(reason="Not yet implemented")
def test_promote_agent_promote_link(staged_env, config):
    target_hash = ApiResponse()
    setattr(target_hash, "commit_hash", "a")
    setattr(target_hash, "distro_hash", "a")

    candidate_hash = "a"
    target_name = "b"
    pa = PromoterAgent(config)
    pa.promote_link(candidate_hash, target_name)
    # verify


def test_no_rollback_needed(staged_env, basic_setup):

    basic_vars = basic_setup()
    attempted_hash = basic_vars.attempted_hash
    target_name = basic_vars.target_name
    transaction = basic_vars.transaction
    pa = basic_vars.pa

    # Imagine the hash was promoted, but transaction end was not called
    # Check we are not Rolling Back
    pa.dlrn_client.promote_hash(attempted_hash, target_name)
    try:
        transaction.rollback()
        assert False, "Rollback should not be needed here"
    except RollbackNotNeeded:
        assert True, "Rollback correclty refused"

    # Check that promotion was really left untouched
    h = pa.dlrn_client.fetch_hash(target_name)
    error_msg = "Hash was touched after rollback rejected"
    assert h == attempted_hash, error_msg

def test_promote_retry(basic_setup):

    basic_vars = basic_setup()
    attempted_hash = basic_vars.attempted_hash
    target_name = basic_vars.target_name
    rollback_hash = basic_vars.rollback_hash
    transaction = basic_vars.transaction
    pa = basic_vars.pa

    # Now simulate that almost everything was promoted except for
    # dlrn link
    # TODO(gcerami) at this point it would be really better to reattempt the
    # dlrn_promotion ...

    # Rollback is allowed to retry promotion and it should
    dlrn_hash = transaction.rollback(retry_promotion=True)
    error_msg = ("Wrong valid state hash returned: {} should be {}"
                "".format(dlrn_hash, attempted_hash))
    assert dlrn_hash == attempted_hash, error_msg
    res = pa.dlrn_client.validate_hash(attempted_hash, name=target_name)
    assert res['promotion_valid'], "Hash was not correctly promoted"


@pytest.mark.xfail(raises=RollbackError)
def test_invalid_rollback(basic_setup):
    basic_vars = basic_setup("invalid_hash")
    attempted_hash = basic_vars.attempted_hash
    target_name = basic_vars.target_name
    rollback_hash = basic_vars.rollback_hash
    transaction = basic_vars.transaction
    pa = basic_vars.pa

    # Try to rollback to an invalid state
    # Should raise an error
    dlrn_hash = transaction.rollback(retry_promotion=False)


def test_rollback_everything(basic_setup):
    basic_vars = basic_setup()
    attempted_hash = basic_vars.attempted_hash
    target_name = basic_vars.target_name
    rollback_hash = basic_vars.rollback_hash
    transaction = basic_vars.transaction
    pa = basic_vars.pa

    # Now we try without allowing retry
    # This should rollback everything
    dlrn_hash = transaction.rollback(retry_promotion=False)
    error_msg = ("Wrong valid state hash returned: {} should be {}"
                 "".format(dlrn_hash, rollback_hash))
    assert dlrn_hash == rollback_hash, error_msg
    res = pa.validate_hash(dlrn_hash, name=target_name)
    error_msg = "Reported valid state hash is not valid: {}".format(dlrn_hash)
    assert res['promotion_valid'], error_msg

@pytest.mark.skip(reason="Not implemented yet")
def test_rollback_at_qcow():
    pass

@pytest.mark.skip(reason="Not implemented yet")
def test_rollback_at_containers():
    pass

