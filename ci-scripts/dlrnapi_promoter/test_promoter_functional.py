"""
This test is launched as part of the existing tox command

It tests that the staging environment provisioner is doing a correct
job by looking mainly at its output: the stage file, the directory structure,
the list of containers created.

Uses standard pytest fixture as a setup/teardown method
"""
import dlrn
import dlrnapi_client
import logging
import os
import pytest
import pprint
import stat
import tempfile
import yaml

try:
    import urllib2 as url
except ImportError:
    import urllib.request as url

from dlrn_interface import (DlrnClient, DlrnCommitDistroHash, DlrnClientConfig,
                            DlrnHash, DlrnAggregateHash)
from dlrnapi_promoter import Promoter


from tests.staging_setup.staging_environment import main as stage_main


@pytest.fixture(scope='function', params=['qcow_single', 'qcow_component'])
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

    if "_component" in test_case:
        setup_cmd_line += " --fixtures-file integration-pipeline.yaml"
        teardown_cmd_line += " --fixtures-file integration-pipeline.yaml"

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
                                        "containers_component"),
                         indirect=True)
def test_promote_containers(promoter, staged_env):
    prom = promoter
    stage_info = staged_env
    candidate_dict = stage_info['dlrn']['promotions']['promotion_candidate']
    candidate_hash = DlrnHash(source=candidate_dict)
    candidate_label = candidate_dict['name']
    target_label = stage_info['dlrn']['promotion_target']
    prom.logic.promote(candidate_hash, candidate_label, target_label,
                       allowed_clients=["registries_client"])


@pytest.mark.parametrize("staged_env", ("qcow_single", "qcow_component"),
                         indirect=True)
def test_promote_qcows(promoter, staged_env):
    prom = promoter
    stage_info = staged_env
    distro_name = stage_info['main']['distro_name']
    distro_version = stage_info['main']['distro_version']
    distro = "{}{}".format(distro_name, distro_version)
    release = stage_info['main']['release']
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

    prom.logic.promote(candidate_hash, candidate_label, target_label,
                       allowed_clients=["qcow_client"])

    images_top_root = stage_info['overcloud_images']['root']
    images_top_root = images_top_root.rstrip("/")
    images_root = os.path.join(images_top_root, distro, release, "rdo_trunk")
    promotion_link = os.path.join(images_root, target_label)
    promotion_dir = os.path.join(images_root, candidate_hash.full_hash)
    try:
        file_mode = os.lstat(promotion_link).st_mode
        assert True
    except OSError:
        assert False, "No link was created"

    assert stat.S_ISLNK(file_mode)
    assert os.readlink(promotion_link) == promotion_dir

    current_dict = stage_info['dlrn']['promotions']['currently_promoted']
    current_hash = DlrnHash(source=current_dict)
    previous_dict = stage_info['dlrn']['promotions']['previously_promoted']
    previous_label = previous_dict['name']
    previous_link = os.path.join(images_root, previous_label)
    previous_dir = os.path.join(images_root, current_hash.full_hash)

    try:
        file_mode = os.lstat(previous_link).st_mode
        assert True
    except OSError:
        assert False, "No link was created"

    assert stat.S_ISLNK(file_mode)
    assert os.readlink(previous_link) == previous_dir


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
            hash_list = prom.logic.dlrn_client.fetch_promotions_from_hash(
                dlrn_hash)
            print(hash_list)
        # We don't care about timestamp
        promoted_hash.timestamp = None
        candidate_hash.timestamp = None
        assert promoted_hash == candidate_hash


def test_check_named_hashes_fail():
    assert False


def test_promoter_main():
    # Test legacy promoter is called.
    # TODO mock the check_named_hashes_unchanges
    assert False
