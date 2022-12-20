"""
This test is launched as part of the existing tox command

It tests general workflow with multiple classes from the promoter involved

 Uses standard pytest fixture as a setup/teardown method
"""
import logging
import os

import promoter_integration_checks
import pytest
import yaml
from common import close_logging
from config import PromoterConfigFactory
from dlrn_hash import DlrnAggregateHash, DlrnCommitDistroExtendedHash, DlrnHash
from logic import Promoter
from stage import main as stage_main


COPY_QUAY_CONFIG = """
---
zuul_api: "https://review.rdoproject.org/zuul/api"
pull_registry: {}
push_registry: {}
entries:
 - name: "train"
   release: "train"
   job_name: "periodic-tripleo-ci-build-containers-ubi-9-quay-push-master"
   api_entry: "http://localhost:58080/"
   from_namespace: tripleotraincentos8
   to_namespace: tripleotraincentos8
"""


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

    release_config = "CentOS-8/train.yaml"
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
        scenes = 'dlrn,registries'
        extra_file = "--extra-settings stage-config.yaml"

    setup_cmd_line = " {}".format(extra_file)
    teardown_cmd_line = "{}".format(extra_file)

    if scenes is not None:
        setup_cmd_line += " --scenes {}".format(scenes)

    setup_cmd_line += " setup --release-config {} --setup-release ".format(release_config)
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

    with open(os.path.expanduser('~') + '/config.yaml', 'w') as f:
        f.write(COPY_QUAY_CONFIG.format(stage_info['registries']['source']['url'],
                stage_info['registries']['targets'][0]['url']))

    yield (stage_info, promoter)

    log.info("Running cmd line: {}".format(teardown_cmd_line))
    stage_main(teardown_cmd_line)
    os.remove(os.path.expanduser('~') + '/config.yaml')



@pytest.mark.skip(reason="Copy quay needs fix")
@pytest.mark.parametrize("staged_env", ("containers_single",
                                        "containers_integration"),
                         indirect=True)
def test_promote_containers_copy_quay_client(staged_env):
    """
    Tests promotion of containers using copay_quay_client.
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
                     allowed_clients=["copy_quay_client"])

    promoter_integration_checks.query_container_registry_promotion(
        stage_info=stage_info)


