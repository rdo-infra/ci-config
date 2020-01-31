"""
This test is launched as part of the existing tox command

It tests if promoter and dlrn server are interacting correctly

Uses standard pytest fixture as a setup/teardown method
"""

import logging
import os
import pytest
import pprint
import promoter_integration_checks
import yaml

from common import close_logging

try:
    import urllib2 as url
except ImportError:
    import urllib.request as url

from dlrnapi_client.rest import ApiException
from dlrn_hash import DlrnCommitDistroHash, DlrnAggregateHash, DlrnHash
from logic import Promoter
from stage import main as stage_main


@pytest.fixture(scope='function', params=['dlrn_single', 'dlrn_integration'])
def staged_env(request):
    """
    Fixture that runs the staging environment provisioner with parameters,
    yield the stage_info file produced and cleans up after
    It has two parameters by default, to test the interaction for single
    pipeline and for integration pipeline
    :return: yields the stage_info dict
    """
    close_logging("promoter-staging")
    close_logging("promoter")
    log = logging.getLogger('promoter-staging')

    # We are going to call the main in the staging passing a composed command
    # line, so we are testing also that the argument parsing is working
    # correctly instead of passing  configuration directly
    config_file = "stage-config-secure.yaml"
    promoter_config_file = \
        "CentOS-7/master.ini"
    setup_cmd_line = "setup --stage-config-file {}".format(config_file)
    teardown_cmd_line = "teardown --stage-config-file {}".format(config_file)

    try:
        test_case = request.param
    except AttributeError:
        pass
    except KeyError:
        log.error("Invalid test case '{}'".format(request.param))
        raise

    scenes = 'dlrn'
    setup_cmd_line += " --scenes {}".format(scenes)

    # for the tests of the integration pipeline we need to pass a different
    # file with db data
    if "_integration" in test_case:
        promoter_config_file = \
            "CentOS-8/master.ini"
        setup_cmd_line += " --db-data integration-pipeline.yaml"
        teardown_cmd_line += " --db-data integration-pipeline.yaml"

    log.info("Running cmd line: {}".format(setup_cmd_line))

    config = stage_main(setup_cmd_line)

    stage_info_path = config.main['stage_info_path']
    with open(stage_info_path, "r") as stage_info_file:
        stage_info = yaml.safe_load(stage_info_file)

    overrides = {
        'log_file': stage_info['main']['log_file'],
        'repo_url': stage_info['dlrn']['server']['repo_url'],
        'promotion_steps_map': {
            'tripleo-ci-staging-promoted': 'tripleo-ci-staging',
        },
        'promotion_criteria_map': {
            'tripleo-ci-staging-promoted': [
                'staging-job-1',
                'staging-job-2',
            ]
        },
        'api_url': stage_info['dlrn']['server']['api_url'],
        'username': stage_info['dlrn']['server']['username']
    }
    print(stage_info['dlrn']['server']['username'])

    overrides_obj = type("FakeArgs", (), overrides)
    os.environ["DLRNAPI_PASSWORD"] = stage_info['dlrn']['server']['password']
    promoter = Promoter(promoter_config_file, overrides=overrides_obj)

    yield stage_info, promoter

    log.info("Running cmd line: {}".format(teardown_cmd_line))
    stage_main(teardown_cmd_line)


@pytest.mark.serial
def test_dlrn_server(staged_env):
    """
    General server testing, with a single promotion
    :param staged_env: The staged env fixture
    :return: None
    """
    stage_info, promoter = staged_env
    commit = stage_info['dlrn']['promotions']['promotion_candidate']
    candidate_label = commit['name']
    promote_name = stage_info['dlrn']['promotion_target']
    repo_url = stage_info['dlrn']['server']['repo_url']

    client = promoter.dlrn_client
    dlrn_hash = DlrnHash(source=commit)

    # TODO: Check db injection (needs sqlite3 import)
    #  Check we can access dlrnapi
    try:
        client.promote(dlrn_hash, promote_name,
                       candidate_label=candidate_label, create_previous=False)
        assert True, "Dlrn api responding"
    except ApiException as e:
        msg = "Exception when calling DefaultApi->api_promote_post: %s\n" % e
        assert False, msg

    # Check if we can access repo_url and get the versions file
    versions_url = os.path.join(repo_url, promote_name, 'versions.csv')
    try:
        url.urlopen(versions_url)
        assert True, "Versions file found"
    except IOError:
        assert False, "No versions file generated"


@pytest.mark.serial
def test_select_candidates(staged_env):
    """
    Testing the selection of candidates hashes after fetching them from
    the server
    :param staged_env: The staged env fixture
    :param promoter: The promoter fixture
    :return: None
    """
    stage_info, promoter = staged_env

    candidate_hashes_list = []
    for target_label, candidate_label in \
            promoter.config.promotion_steps_map.items():
        candidate_hashes_list = promoter.select_candidates(candidate_label,
                                                           target_label)
    assert candidate_hashes_list != []

    if stage_info['main']['pipeline_type'] == "integration":
        assert type(candidate_hashes_list[0]) == DlrnAggregateHash
    elif stage_info['main']['pipeline_type'] == "single":
        assert type(candidate_hashes_list[0]) == DlrnCommitDistroHash


def test_promote_all_links(staged_env):
    """
    Testing the promotion of candidates inside promote_all_links, but limited
    to the dlrn part
    :param staged_env: The staged env fixture
    :param promoter: The promoter fixture
    :return: None
    """
    stage_info, promoter = staged_env

    promoted_pairs = promoter.promote_all()
    error_msg = "Nothing promoted"
    assert promoted_pairs != [()], error_msg
    for promoted_hash, label in promoted_pairs:
        dlrn_hash = DlrnHash(source=stage_info['dlrn']['commits'][-1])
        if stage_info['main']['pipeline_type'] == "single":
            candidate_hash = dlrn_hash
            error_msg = "Single pipeline should promote a commit/distro hash"
            assert type(promoted_hash) == DlrnCommitDistroHash, error_msg
        elif stage_info['main']['pipeline_type'] == "integration":
            candidate_hash = \
                promoter.dlrn_client.fetch_promotions_from_hash(dlrn_hash,
                                                                count=1)
            error_msg = "Integration pipeline should promote an aggregate hash"
            assert type(promoted_hash) == DlrnAggregateHash, error_msg
        # We don't care about timestamp
        promoted_hash.timestamp = None
        candidate_hash.timestamp = None
        assert promoted_hash == candidate_hash

        promoter_integration_checks.check_dlrn_promoted_hash(
            stage_info=stage_info)
