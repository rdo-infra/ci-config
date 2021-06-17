"""
This test is launched as part of the existing tox command

It tests the function used to check both the promoter-staging integration job
and the functional tests on the promoter

Uses standard pytest fixture as a setup/teardown method
"""

import logging
import os

import dlrnapi_client
import pytest

try:
    import urllib2 as url_libc  # pylint: disable=unused-import
except ImportError:
    import urllib.request as url_lib

import yaml
from promoter.dlrn_hash import (DlrnAggregateHash,
                                DlrnCommitDistroExtendedHash, DlrnHash)
from stage.stage_server import main as stage_main

from .promoter_integration_checks import (check_dlrn_promoted_hash,
                                          compare_tagged_image_hash,
                                          parse_promotion_logs,
                                          query_container_registry_promotion)

try:
    # Python3 imports
    from unittest.mock import patch

    builtin_str = "builtins.open"
except ImportError:
    # Python2 imports
    from mock import patch

    builtin_str = "__builtin__.open"


@pytest.fixture(scope='function')
def staged_env(request):
    """
    Fixture that runs the staging environment provisioner with parameters,
    yield the stage_info file produced and cleans up after
    It has two parameters by default, to test the interaction for single
    pipeline and for integration pipeline
    :param request: the parameter for the fixture, passed by the
    pytest.mark.parametrize decorator above each test
    :return: yields the stage_info dict
    """

    log = logging.getLogger('promoter-staging')

    # We are going to call the main in the staging passing a composed command
    # line, so we are testing also that the argument parsing is working
    # correctly instead of passing  configuration directly
    # extra_file = "stage-config-secure.yaml"
    release_config = "CentOS-7/master.yaml"
    try:
        test_case = request.param
    except AttributeError:
        pass
    except KeyError:
        log.error("Invalid test case '{}'".format(request.param))
        raise

    # Select scenes to run in the staging env depending on the parameter passed
    # to the fixture
    scenes = None
    if "overcloud_" in test_case:
        scenes = 'overcloud_images'
    if "registries_" in test_case:
        scenes = 'registries'
    if "containers_" in test_case:
        scenes = 'dlrn,registries,containers'

    setup_cmd_line = ""
    teardown_cmd_line = ""
    if scenes is not None:
        setup_cmd_line += " --scenes {}".format(scenes)

    if "_integration" in test_case:
        release_config = "CentOS-8/master.yaml"
        # for the tests of the integration pipeline we need to pass a different
        # file with db data
        setup_cmd_line += " --db-data-file integration-pipeline.yaml"
        teardown_cmd_line += " --db-data-file integration-pipeline.yaml"

    setup_cmd_line += " setup --release-config {}".format(release_config)
    teardown_cmd_line += " teardown "

    log.info("Running cmd line: {}".format(setup_cmd_line))

    config = stage_main(setup_cmd_line)

    stage_info_path = config['stage_info_path']
    with open(stage_info_path, "r") as stage_info_file:
        stage_info = yaml.safe_load(stage_info_file)

    yield stage_info
    log.info("Running cmd line: {}".format(teardown_cmd_line))
    stage_main(teardown_cmd_line)


@pytest.mark.parametrize("staged_env", ("dlrn_single",
                                        "dlrn_integration"),
                         indirect=True)
def test_dlrn_promoted(staged_env):
    """
    Checks that candidate hashes in dlrn have been promoted
    And others did not promote
    :param staged_env: The staged_env fixture
    :return: None
    """
    stage_info = staged_env
    promotion_dict = stage_info['dlrn']['promotions']['promotion_candidate']
    promotion_hash = DlrnHash(source=promotion_dict)

    with patch.object(dlrnapi_client.DefaultApi, 'api_promotions_get') as \
            mock_api:
        # positive test

        promotion_hash.promote_name = "tripleo-ci-staging-promoted"
        mock_api.return_value = [promotion_hash]
        check_dlrn_promoted_hash(stage_info=stage_info)

        # negative test
        promotion_hash.promote_name = "tripleo-ci-staging"
        mock_api.return_value = [promotion_hash]
        with pytest.raises(AssertionError):
            check_dlrn_promoted_hash(stage_info=stage_info)


@pytest.mark.parametrize("staged_env", ("containers_single",
                                        "containers_integration"),
                         indirect=True)
def test_query_container(staged_env):
    """
    tests the check that checks if containers have been promoted successfully
    :param staged_env: The staged_env fixture
    :return: None
    """
    stage_info = staged_env
    with patch.object(url_lib, 'urlopen') as mock_urllib:
        # positive tests
        mock_urllib.return_value = True
        query_container_registry_promotion(stage_info=stage_info)
        # negative tests
        mock_urllib.side_effect = url_lib.HTTPError(*[None] * 5)
        with pytest.raises(AssertionError):
            query_container_registry_promotion(stage_info=stage_info)


@pytest.mark.xfail(reason="needs revisiting, much more difficult to make it "
                          "pass now")
@pytest.mark.parametrize("staged_env", ("qcow_single",
                                        "qcow_integration"),
                         indirect=True)
# @patch('pysftp')
def test_compare_tagged(staged_env):
    stage_info = staged_env
    with patch('os.readlink') as mock_readlink:
        mock_readlink.return_value = (
            "/tmp/promoter-staging/overcloud_images/centos7/master"
            "/rdo_trunk/360d335e94246d7095672c5aa92b59afa380a059_9e598812"
        )
        compare_tagged_image_hash(stage_info=stage_info)


success_pattern_container_positive_single_pipeline = (
    "Candidate hash 'commit: 360d335e94246d7095672c5aa92b59afa380a059, "
    "distro: 9e5988125e88f803ba20743be7aa99079dd275f2, extended: None, "
    "component: None, "
    "timestamp: None': criteria met, attempting promotion to "
    "tripleo-ci-staging-promoted\n"
    "Qcow promote 'commit: 360d335e94246d7095672c5aa92b59afa380a059, distro:"
    " 9e5988125e88f803ba20743be7aa99079dd275f2, extended: None, "
    "component: None, "
    "timestamp: None' to tripleo-ci-staging-promoted: Successful promotion\n"
    "Candidate hash 'commit: 360d335e94246d7095672c5aa92b59afa380a059, "
    "distro: 9e5988125e88f803ba20743be7aa99079dd275f2, extended: None, "
    "component: None, "
    "timestamp: None': SUCCESSFUL promotion to tripleo-ci-staging-promoted\n"
    "promoter SUCCESS promoting centos7-master tripleo-ci-staging as"
    " tripleo-ci-staging-promoted \n"
    "Containers promote 'commit: 360d335e94246d7095672c5aa92b59afa380a059, "
    "distro: 9e5988125e88f803ba20743be7aa99079dd275f2, extended: None, "
    "component: None, "
    "timestamp: None' to tripleo-ci-staging-promoted: Successful promotion\n"
    "Summary: Promoted 1 hashes this round\n"
    "Promoter terminated normally\n"
)

success_pattern_container_positive_integration_pipeline = (
    "Candidate hash 'aggregate: a81d9c8fe0347b577d363e8b14c900ba, "
    "commit: 360d335e94246d7095672c5aa92b59afa380a061, distro: "
    "9e5988125e88f803ba20743be7aa99079dd275f4, component: None, timestamp:"
    " 1583239777': criteria met, attempting promotion to"
    " tripleo-ci-staging-promoted\n"
    "Qcow promote 'aggregate: a81d9c8fe0347b577d363e8b14c900ba, "
    "commit: 360d335e94246d7095672c5aa92b59afa380a061, "
    "distro: 9e5988125e88f803ba20743be7aa99079dd275f4, component: None, "
    "timestamp: None' to tripleo-ci-staging-promoted: Successful promotion\n"
    "Candidate hash 'aggregate: a81d9c8fe0347b577d363e8b14c900ba, commit: "
    "360d335e94246d7095672c5aa92b59afa380a061, distro: "
    "9e5988125e88f803ba20743be7aa99079dd275f4, component: None, "
    "timestamp: None': SUCCESSFUL promotion to tripleo-ci-staging-promoted\n"
    "Containers promote 'aggregate: a81d9c8fe0347b577d363e8b14c900ba, commit: "
    "360d335e94246d7095672c5aa92b59afa380a061, distro: "
    "9e5988125e88f803ba20743be7aa99079dd275f4, component: None, "
    "timestamp: None' to tripleo-ci-staging-promoted: Successful promotion\n"
    "Summary: Promoted 1 hashes this round\n"
    "Promoter terminated normally\n"
)


@pytest.mark.parametrize("staged_env", ("dlrn_single",
                                        "dlrn_integration"),
                         indirect=True)
def test_parse(staged_env):
    """
    Checks if success and failure patterns are present in the logs.
    :param staged_env: The staged_env fixture
    :return: None
    """
    stage_info = staged_env
    candidate_dict = stage_info['dlrn']['promotions']['promotion_candidate']
    candidate_hash = DlrnHash(source=candidate_dict)
    if type(candidate_hash) is DlrnCommitDistroExtendedHash:
        with open(os.path.expanduser(stage_info['main']['log_file']),
                  "w") as log_file:
            log_file.write(success_pattern_container_positive_single_pipeline)
    elif type(candidate_hash) is DlrnAggregateHash:
        with open(os.path.expanduser(stage_info['main']['log_file']),
                  "w") as log_file:
            log_file.write(
                success_pattern_container_positive_integration_pipeline)

    parse_promotion_logs(stage_info=stage_info)


@pytest.mark.xfail(reason="Test not implemented")
def test_main():
    assert False
