"""
This test is launched as part of the existing tox command

It tests that the staging environment provisioner is doing a correct
job by looking mainly at its output: the stage file, the directory structure,
the list of containers created.

Uses standard pytest fixture as a setup/teardown method
"""
import docker
import logging
import os
import pytest
import pprint
try:
    import urllib2 as url
except ImportError:
    import urllib.request as url
import yaml

try:
    from unittest.mock import Mock, patch
    import unittest.mock as mock
except ImportError:
    from mock import Mock, patch
    import mock

from staging_environment import StageConfig, main as stage_main
from dlrn_hash import DlrnCommitDistroHash, DlrnAggregateHash, DlrnHash

log = logging.getLogger("Test Staging")


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

    # We are going to call the main in the staging passing a composed command
    # line, so we are testing also that the argument parsing is working
    # correctly instead of passing  configuration directly
    test_case = "all_single"
    config_file = "stage-config-secure.yaml"
    setup_cmd_line = "setup --stage-config-file {}".format(config_file)
    teardown_cmd_line = "teardown --stage-config-file {}".format(config_file)

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
        scenes = 'registries,containers'
    if scenes is not None:
        setup_cmd_line += " --scenes {}".format(scenes)

    # for the tests of the integration pipeline we need to pass a different
    # file with db data
    if "_integration" in test_case:
        setup_cmd_line += " --db-data-file integration-pipeline.yaml"
        teardown_cmd_line += " --db-data-file integration-pipeline.yaml"

    log.info("Running cmd line: {}".format(setup_cmd_line))

    config = stage_main(setup_cmd_line)

    stage_info_path = config.main['stage_info_path']
    with open(stage_info_path, "r") as stage_info_file:
        stage_info = yaml.safe_load(stage_info_file)

    yield config, stage_info

    log.info("Running cmd line: {}".format(teardown_cmd_line))
    stage_main(teardown_cmd_line)

    # Check that teardown works properly
    if "registries" in stage_info['main']['scenes']:
        # Check registries are correctly cleared after teardown
        docker_client = docker.from_env()
        for registry in config.registries:
            try:
                docker_client.containers.get(registry['name'])
                assert False, "Registry {} not removed".format(registry['name'])
            except docker.errors.NotFound:
                assert True
        # There are other resources the staging environment creates
        # We should make sure that the rest of teardown works correctly:
        # TODO(gcerami) Check that the images tree is removed
        # TODO(gcerami) Check that stage-info.yaml file is removed.
        # TODO(gcerami) Check that dlrn commit database is removed

    # TODO(gcerami) Check that dlrn commit database is removed


@pytest.mark.serial
def test_stage_config():
    """
    Test to see if the stage config is created correctly
    :return: None
    """
    config = StageConfig(source="stage-config-secure.yaml")
    config_sections = ['dlrn', 'registries', 'containers', 'main',
                       'overcloud_images']
    for section in config_sections:
        assert hasattr(config, section)
        assert (getattr(config, section) is not None)


@pytest.mark.parametrize("staged_env",
                         ('all_single', 'all_integration'),
                         indirect=True)
@pytest.mark.serial
def test_stage_info(staged_env):
    """
    Test that the staged env is producing valid stage_info
    :param staged_env: The staged_env fixture
    :return: None
    """
    config, stage_info = staged_env

    # Check needed top level attributes
    sections = [
        "dlrn",
        "overcloud_images",
        "registries",
        "containers"
    ]
    for attribute in sections:
        assert attribute in stage_info.keys()
    main_attributes = [
        "distro_name",
        "distro_version",
        "release",
        "log_file",
    ]
    for attribute in main_attributes:
        msg = "No {} in main".format(attribute)
        assert attribute in stage_info['main'].keys(), msg
    dlrn_attributes = [
        'api_url',
        'repo_url',
    ]
    for attribute in dlrn_attributes:
        msg = "No {} in dlrn.server".format(attribute)
        assert attribute in stage_info['dlrn']['server'].keys(), msg


@pytest.mark.parametrize("staged_env",
                         ('registries_single', 'registries_integration'),
                         indirect=True)
@pytest.mark.serial
def test_registries(staged_env):
    """
    Test that the registries are created correctly
    :param staged_env: The staged_env fixture
    :return: None
    """

    docker_client = docker.from_env()
    config, stage_info = staged_env

    # Check registries
    for registry in config.registries:
        # Check compliance with config file, all registries should be there
        if registry['type'] == "source":
            source_registry_name = stage_info['registries']['source']['name']
            assert registry['name'] == source_registry_name
        else:
            found = False
            for target in stage_info['registries']['targets']:
                if registry['name'] == target['name']:
                    found = True
                    if registry['secure']:
                        # Check that registry marked as secure
                        # have a auth_url defined
                        assert "auth_url" in target
                        # And we can log in with info provided
                        try:
                            docker_client.login(
                                registry=target['auth_url'],
                                username=target['username'],
                                password=target['password'],
                                dockercfg_path="/dev/null",
                                reauth=True
                            )
                        except docker.errors.APIError:
                            assert False, "Login failed"
            assert found
        # Check that the registries are up and running
        assert docker_client.containers.get(registry['name'])
        # TODO(gcerami) Check registries respond correctly
    all_reg = (stage_info['registries']['targets']
               + [stage_info['registries']['source']])
    for registry in all_reg:
        # Check needed attributes
        attributes = [
            "host",
            "name",
            "namespace",
            "username",
            "password",
        ]
        for attribute in attributes:
            assert attribute in registry


@pytest.mark.parametrize("staged_env",
                         ('containers_single', 'containers_integration'),
                         indirect=True)
@pytest.mark.serial
def test_containers(staged_env):
    """
    Test that the containers are created and pushed correctly to local source
    registry
    :param staged_env: The staged_env fixture
    :return: None
    """
    __, stage_info = staged_env
    # Check that all declare containers are realy pushed
    ppc64le_count = 0
    found = []
    source_registry = stage_info['registries']['source']['url']

    for full_name in stage_info['containers']['images']:
        # Check if we only upload the containers for the promotion candidate
        # hash
        candidate_hash_dict =\
            stage_info['dlrn']['promotions']['promotion_candidate']
        candidate_hash = DlrnHash(source=candidate_hash_dict)
        if stage_info['main']['pipeline_type'] == "integration":
            assert type(candidate_hash) == DlrnAggregateHash
        elif stage_info['main']['pipeline_type'] == "single":
            assert type(candidate_hash) == DlrnCommitDistroHash

        assert candidate_hash.full_hash in full_name

        container, tag = full_name.split(':')
        reg_url = "{}/v2/{}/manifests/{}".format(
            source_registry, container, tag
        )
        if "_ppc64le" in tag:
            ppc64le_count += 1
        try:
            url.urlopen(reg_url)
            found.append(full_name)
        except url.HTTPError:
            print("Missing container: {}".format(reg_url))
    assert sorted(stage_info['containers']['images']) == sorted(found)

    # check that at least one image doesn't have ppc tagging
    # If all images have ppcle tagging, the should be at least one third
    # Check that they are way less
    images_count = len(stage_info['containers']['images'])
    ppc64le_ratio = float(ppc64le_count) / images_count
    assert ppc64le_ratio <= 1.0 / 3.0


@pytest.mark.parametrize("staged_env",
                         ('overcloud_single', 'overcloud_integration'),
                         indirect=True)
@pytest.mark.serial
def test_overcloud_images(staged_env):
    """
    Test that the staged hierarchy of overcloud images was created correctly
    :param staged_env: The staged_env fixture
    :return: None
    """
    config, stage_info = staged_env
    # Check images subtree, all full hases should be there
    overcloud_images_path = config.overcloud_images['root']
    base_path = os.path.join(
        overcloud_images_path,
        config.main['distro'],
        config.main['release'],
        'rdo_trunk',
    )
    # Check stage_info has the requred attributes
    overcloud_images = stage_info['overcloud_images']
    attributes = [
        'user',
        'key_path',
        'root'
    ]
    for attribute in attributes:
        assert attribute in overcloud_images
    check_paths = []
    existing_paths = []
    for commit in stage_info['dlrn']['promotions'].values():
        dlrn_hash = DlrnHash(source=commit)
        # check commit attributes are there
        hash_path = os.path.join(base_path, dlrn_hash.full_hash)
        check_paths.append(hash_path)

        # We don't block at the first path found, I want to see all
        # the missing paths
        try:
            os.stat(hash_path)
            existing_paths.append(hash_path)
        except OSError:
            raise

    assert check_paths == existing_paths

    # check if we have a leaf with the symbolic link
    # and the dir linked exists
    promotion_commit = \
        stage_info['dlrn']['promotions']['currently_promoted']
    promotion_name = promotion_commit['name']
    promotion_link = os.path.join(base_path, promotion_name)
    promotion_target = os.readlink(promotion_link)
    # The fist commit is "the current promotion link"
    dlrn_hash = DlrnHash(source=promotion_commit)
    sample_path = \
        os.path.join(base_path, dlrn_hash.full_hash)
    assert promotion_target == sample_path
