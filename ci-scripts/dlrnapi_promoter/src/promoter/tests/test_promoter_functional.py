"""
This test is launched as part of the existing tox command

It tests general workflow with multiple classes from the promoter involved

 Uses standard pytest fixture as a setup/teardown method
"""
import logging
import os

import pytest
import yaml
from promoter.common import close_logging
from promoter.config import PromoterConfigFactory
from promoter.dlrn_hash import (DlrnAggregateHash,
                                DlrnCommitDistroExtendedHash, DlrnHash)
from promoter.logic import Promoter
from stage.stage_server import main as stage_main

from . import promoter_integration_checks


@pytest.fixture(scope='function')
def staged_env(request):
    """
    Fixture that runs the staging environment provisioner with parameters,
    yield the stage_info file produced and a promoter configured to use it
    and cleans up after
    It has two parameters by default, to test the interaction for single
    pipeline and for integration pipeline
    :param request: the parameter for the fixture, passed by the
    pytest.mark.parametrize decorator above each test
    :return: yields the stage_info dict and a promoter object
    """

    # With a series of test ir rapid sequence but in the same test instance,
    # logging configuration is passed from env to env, but log file won't be
    # there anymore, so we need to close the logging handlers
    close_logging("promoter-staging")
    close_logging("promoter")
    log = logging.getLogger('promoter-staging')

    # We are going to call the main in the staging passing a composed command
    # line, so we are testing also that the argument parsing is working
    # correctly instead of passing  configuration directly

    # TODO (akahat) Need to enable legacy non integration pipeline coverage.

    release_config = "CentOS-8/master.yaml"
    test_case = "all_integration"

    try:
        test_case = request.param
    except AttributeError:
        pass
    except KeyError:
        log.error("Invalid test case '{}'".format(request.param))
        raise

    # Select scenes to run in the staging env depending on the parameter passed
    # to the fixture
    extra_file = ""
    scenes = None
    if "all_" in test_case:
        extra_file = "--extra-settings stage-config.yaml"
    if "qcow_" in test_case:
        scenes = 'dlrn,overcloud_images'
    if "registries_" in test_case:
        scenes = 'registries'
    if "containers_" in test_case:
        scenes = 'dlrn,registries,containers'
        extra_file = "--extra-settings stage-config.yaml"

    setup_cmd_line = " {}".format(extra_file)
    teardown_cmd_line = "{}".format(extra_file)

    if scenes is not None:
        setup_cmd_line += " --scenes {}".format(scenes)

    setup_cmd_line += " setup --release-config {}".format(release_config)
    teardown_cmd_line += " teardown "
    experimental = 'false'
    if "_experimental" in test_case:
        experimental = 'true'
    # for the tests of the integration pipeline we need to pass a different
    # file for component db data, and emulate CentOS8/master at least
    log.info("Running cmd line: {}".format(setup_cmd_line))

    config = stage_main(setup_cmd_line)

    stage_info_path = config['stage_info_path']
    with open(stage_info_path, "r") as stage_info_file:
        stage_info = yaml.safe_load(stage_info_file)

    overrides = {
        'log_file': stage_info['main']['log_file'],
        'repo_url': stage_info['dlrn']['server']['repo_url'],
        'log_level': 'DEBUG',
        'experimental': experimental,
        'default_qcow_server': 'local',
        'config_file': release_config,
    }
    if "containers_" in test_case:
        overrides['containers_list_base_url'] = \
            stage_info['containers']['containers_list_base_url']

    overrides_obj = type("FakeArgs", (), overrides)
    os.environ["DLRNAPI_PASSWORD"] = stage_info['dlrn']['server']['password']

    config_builder = PromoterConfigFactory()
    config = config_builder("staging", release_config,
                            cli_args=overrides_obj)

    promoter = Promoter(config)

    # Reflect config changes in to the stage server
    # This might cause some test failures
    target_label = [i.strip() for i in promoter.config.promotions.keys()][0]
    stage_updates = {
        'target_label': target_label,
        'candidate_label': promoter.config.promotions[
            target_label]['candidate_label'],
        'criteria': promoter.config.promotions[target_label]['criteria'],
    }

    # TODO (akahat): Refresh stage info dict with config update

    stage_info['dlrn']['promotions'][
        'promotions_candidate'] = stage_updates['candidate_label']
    stage_info['dlrn']['promotions_target'] = target_label

    yield (stage_info, promoter)

    log.info("Running cmd line: {}".format(teardown_cmd_line))
    stage_main(teardown_cmd_line)


@pytest.mark.parametrize("staged_env", ("containers_single",
                                        "containers_integration"),
                         indirect=True)
def test_promote_containers(staged_env):
    """
    Tests promotion of containers
    :param staged_env: The stage env fixture
    :return: None
    """
    stage_info, promoter = staged_env
    candidate_dict = stage_info['dlrn']['promotions']['promotion_candidate']
    candidate_hash = DlrnHash(source=candidate_dict)
    candidate_label = candidate_dict['name']
    target_label = stage_info['dlrn']['promotion_target']
    promoter.dlrn_client.fetch_current_named_hashes(store=True)
    promoter.promote(candidate_hash, candidate_label, target_label,
                     allowed_clients=["registries_client"])

    promoter_integration_checks.query_container_registry_promotion(
        stage_info=stage_info)


@pytest.mark.parametrize("staged_env", ("qcow_single",
                                        "qcow_integration"),
                         indirect=True)
def test_promote_qcows(staged_env):
    """
    Tests promotion of overcloud images
    :param staged_env: The stage env fixture
    :return: None
    """
    stage_info, promoter = staged_env
    candidate_dict = stage_info['dlrn']['promotions']['promotion_candidate']
    candidate_hash = DlrnHash(source=candidate_dict)

    if stage_info['main']['pipeline_type'] == "single":
        error_msg = "Single pipeline should promote a commit/distro hash"
        assert type(candidate_hash) == DlrnCommitDistroExtendedHash, error_msg
    else:
        error_msg = "Integration pipeline should promote an aggregate hash"
        assert type(candidate_hash) == DlrnAggregateHash, error_msg

    target_label = stage_info['dlrn']['promotion_target']

    promoter.dlrn_client.fetch_current_named_hashes(store=True)
    promoter.qcow_client.promote(candidate_hash, target_label)

    promoter_integration_checks.compare_tagged_image_hash(stage_info=stage_info)


# These are the closest test to integration jobs
def test_single_promote(staged_env):
    stage_info, promoter = staged_env

    candidate_dict = stage_info['dlrn']['promotions']['promotion_candidate']
    candidate_hash = DlrnHash(source=candidate_dict)

    promoter.promote(candidate_hash, "tripleo-ci-staging",
                     "tripleo-ci-staging-promoted")


@pytest.mark.parametrize("staged_env", ("all_single",
                                        "all_integration"),
                         indirect=True)
def test_promote_all(staged_env):
    """
    Tests promotion of candidate hash in all its part: dlrn, images, containers
    :param staged_env: The stage env fixture
    :return: None
    """
    stage_info, promoter = staged_env

    promoted_pairs = promoter.promote_all()

    promoter_integration_checks.compare_tagged_image_hash(
        stage_info=stage_info)
    promoter_integration_checks.query_container_registry_promotion(
        stage_info=stage_info)
    promoter_integration_checks.check_dlrn_promoted_hash(
        stage_info=stage_info)
    promoter_integration_checks.parse_promotion_logs(stage_info=stage_info)

    error_msg = "Nothing promoted, and checks did not complain"
    assert len(promoted_pairs) != 0, error_msg


@pytest.mark.parametrize("staged_env", ("all_single",
                                        "all_integration"),
                         indirect=True)
@pytest.mark.xfail(reason="Not Implemented", run=False)
def test_promote_all_no_promotions(staged_env):
    """
    This test should add a second promotion step with criteria, to verify
    taht we can actually perform two promotions in a row.
    It's not easy, as the staging environment needs to support a second
    promotion candidate
    :param staged_env:
    :return:
    """
    assert False


@pytest.mark.parametrize("staged_env", ("all_single",
                                        "all_integration"),
                         indirect=True)
@pytest.mark.xfail(reason="Not Implemented", run=False)
def test_promote_all_two_promotions_in_a_row(staged_env):
    """
    This test should add a second promotion step with criteria, to verify
    taht we can actually perform two promotions in a row.
    It's not easy, as the staging environment needs to support a second
    promotion candidate
    :param staged_env:
    :return:
    """
    assert False
