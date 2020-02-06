"""
This test is launched as part of the existing tox command

It tests that the staging environment provisioner is doing a correct
job by looking mainly at its output: the stage file, the directory structure,
the list of containers created.

Uses standard pytest fixture as a setup/teardown method
"""
import logging
import os
import pytest
import pprint
import tempfile
import yaml
import promoter_integration_checks

try:
    import urllib2 as url
except ImportError:
    import urllib.request as url

from dlrn_interface import (DlrnClient, DlrnCommitDistroHash, DlrnClientConfig,
                            DlrnHash, DlrnAggregateHash)
from dlrnapi_promoter import Promoter

from staging_environment import main as stage_main


@pytest.fixture(scope='function')
def staged_env(request):
    """
    Fixture that runs the staging environment provisioner, yields the files
    produced and cleans up after
    """

    log = logging.getLogger('promoter-staging')

    config_file = "stage-config-secure.yaml"
    try:
        test_case = request.param
    except AttributeError:
        pass
    except KeyError:
        log.error("Invalid test case '{}'".format(request.param))
        raise

    scenes = None
    if "all_" in test_case:
        config_file = "stage-config.yaml"
    if "overcloud_" in test_case:
        scenes = 'overcloud_images'
    if "registries_" in test_case:
        scenes = 'registries'
    if "containers_" in test_case:
        scenes = 'dlrn,registries,containers'
        config_file = "stage-config.yaml"

    setup_cmd_line = "setup --stage-config-file {}".format(config_file)
    teardown_cmd_line = "teardown --stage-config-file {}".format(config_file)
    if scenes is not None:
        setup_cmd_line += " --scenes {}".format(scenes)

    if "_integration" in test_case:
        setup_cmd_line += " --db-data integration-pipeline.yaml"
        teardown_cmd_line += " --db-data integration-pipeline.yaml"

    log.info("Running cmd line: {}".format(setup_cmd_line))

    config = stage_main(setup_cmd_line)

    stage_info_path = config.main['stage_info_path']
    with open(stage_info_path, "r") as stage_info_file:
        stage_info = yaml.safe_load(stage_info_file)

    yield stage_info
    log.info("Running cmd line: {}".format(teardown_cmd_line))
    stage_main(teardown_cmd_line)


ini_config = '''
[main]
distro_name: centos
distro_version: 7
release: master
api_url: http://localhost:58080
username: foo
dry_run: false
log_file: /dev/null
latest_hashes_count: 10
manifest_push: true

[promote_from]
tripleo-ci-staging-promoted: tripleo-ci-staging

[tripleo-ci-staging-promoted]
staging-job-1
staging-job-2
'''


@pytest.fixture(scope='session')
def promoter():

    fp, filepath = tempfile.mkstemp(prefix="ini_conf_test")
    with os.fdopen(fp, "w") as test_file:
        test_file.write(ini_config)

    fakeargs = type("FakeArgs", (), dict(config_file=filepath))
    os.environ["DLRNAPI_PASSWORD"] = "dlrnapi_password00"
    promoter = Promoter(fakeargs)

    yield promoter

    os.unlink(filepath)


@pytest.mark.parametrize("staged_env", ("containers_single",
                                        "containers_integration"),
                         indirect=True)
def test_promote_containers(promoter, staged_env):
    prom = promoter
    stage_info = staged_env
    candidate_dict = stage_info['dlrn']['promotions']['promotion_candidate']
    candidate_hash = DlrnHash(source=candidate_dict)
    candidate_label = candidate_dict['name']
    target_label = stage_info['dlrn']['promotion_target']
    prom.logic.dlrn_client.fetch_current_named_hashes(store=True)
    prom.logic.promote(candidate_hash, candidate_label, target_label,
                       allowed_clients=["registries_client"])

    promoter_integration_checks.query_container_registry_promotion(
        stage_info=stage_info)


@pytest.mark.parametrize("staged_env", ("qcow_single", "qcow_integration"),
                         indirect=True)
def test_promote_qcows(promoter, staged_env):
    prom = promoter
    stage_info = staged_env
    candidate_dict = stage_info['dlrn']['promotions']['promotion_candidate']
    candidate_hash = DlrnHash(source=candidate_dict)

    if stage_info['main']['pipeline_type'] == "single":
        error_msg = "Single pipeline should promote a commit/distro hash"
        assert type(candidate_hash) == DlrnCommitDistroHash, error_msg
    else:
        error_msg = "Integration pipeline should promote an aggregate hash"
        assert type(candidate_hash) == DlrnAggregateHash, error_msg

    candidate_label = candidate_dict['name']
    target_label = stage_info['dlrn']['promotion_target']

    prom.logic.dlrn_client.fetch_current_named_hashes(store=True)
    prom.logic.promote(candidate_hash, candidate_label, target_label,
                       allowed_clients=["qcow_client"])

    promoter_integration_checks.compare_tagged_image_hash(stage_info=stage_info)


@pytest.mark.parametrize("staged_env", ("all_single", "all_integration"),
                         indirect=True)
def test_promote_all_links(staged_env, promoter):
    stage_info = staged_env
    prom = promoter

    promoted_pairs = prom.logic.promote_all_links()
    error_msg = "Nothing promoted"
    assert promoted_pairs != [()], error_msg
    for promoted_hash, label in promoted_pairs:
        dlrn_hash = DlrnHash(source=stage_info['dlrn']['commits'][-1])
        if stage_info['main']['pipeline_type'] == "single":
            candidate_hash = dlrn_hash
        elif stage_info['main']['pipeline_type'] == "integration":
            candidate_hash = prom.logic.dlrn_client.fetch_promotions_from_hash(
                dlrn_hash, count=1)
        # We don't care about timestamp
        promoted_hash.timestamp = None
        candidate_hash.timestamp = None
        assert promoted_hash == candidate_hash
