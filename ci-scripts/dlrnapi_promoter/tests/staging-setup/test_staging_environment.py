"""
This test is launched as part of the existing tox command

It tests that the staging environment provisioner is doing a correct
job by looking mainly at its output: the stage file, the directory structure,
the list of containers created.

Uses standard pytest fixture as a setup/teardown method
"""
import docker
import dlrnapi_client
import os
import pytest
import pprint
import tempfile
import subprocess
try:
    import urllib2 as url
except ImportError:
    import urllib.request as url
import yaml


from staging_environment import StagedEnvironment, load_config
from dlrnapi_client.rest import ApiException


# FIXME(gcerami) I don't know why, but test via tox doesn't honour the scope
# 'session' And the fixture is invoked more than once, so I have to put all the
# tests on a single function


@pytest.fixture(scope='session')
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
    }
    config = load_config(overrides, db_filepath="/tmp/sqlite-test.db")
    staged_env = StagedEnvironment(config)
    staged_env.setup()
    with open(config['stage-info-path'], "r") as stage_info_path:
        stage_info = yaml.safe_load(stage_info_path)

    yield config, stage_info

    staged_env.teardown()


# Uncomment when session fixture works and remove def below
# def test_registries(staged_env):
def test_staging_env(staged_env):

    docker_client = docker.from_env()
    config, stage_info = staged_env

    # os.stat(stage_info[''])
    # TODO(gcerami) Check dlrnapi response (needs to spawn uwsgi+ api)
    # TODO(gcerami) Check db injection (needs sqlite3 import)
    # api_client = dlrnapi_client.ApiClient(host=stage_info['dlrn_host'])
    # dlrnapi_client.configuration.username = 'foo'
    # dlrnapi_client.configuration.password = 'bar'
    # api_instance = dlrnapi_client.DefaultApi(api_client=api_client)

    # params = dlrnapi_client.Promotion()
    # params.commit_hash = \
    #    stage_info['promotions']['promotion_candidate']['commit_hash']
    # params.distro_hash = \
    # stage_info['promotions']['promotion_candidate']['distro_hash']
    # params.distro_hash = stage_info['promotion_target']

    # try:
    #    api_response = api_instance.api_promote_post(params=params)
    #    pprint(api_response)
    # except ApiException as e:
    #    print("Exception when calling DefaultApi->api_promote_post: %s\n" % e)

    # Check neede top level attributes
    attributes = [
        "dlrn_host",
        "promotions",
        "distro",
        "distro_version",
        "overcloud_images",
        "release",
        "logfile",
    ]
    for attribute in attributes:
        assert attribute in stage_info

    # Check registries
    for registry in config['registries']:
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


# Uncomment when session fixture works
# def test_containers(staged_env):
#     config, stage_info = staged_env
    # Check that all decleare containers are realy pushed
    ppc64le_count = 0
    found = []
    source_registry = stage_info['registries']['source']['host']

    for full_name in stage_info['containers']:
        # Check if we only upload the containers for the promotion candidate
        # hash
        candidate_full_hash = \
            stage_info['promotions']['promotion_candidate']['full_hash']
        assert candidate_full_hash in full_name

        container, tag = full_name.split(':')
        reg_url = "http://{}/v2/{}/manifests/{}".format(
            source_registry, container, tag
        )
        if "_ppc64le" in tag:
            ppc64le_count += 1
        try:
            url.urlopen(reg_url)
            found.append(full_name)
        except url.HTTPError:
            print("Missing container: {}".format(reg_url))
    assert sorted(stage_info['containers']) == sorted(found)

    # check that at least one image doesn't have ppc tagging
    # If all images have ppcle tagging, the should be at least one third
    # Check that they are way less
    images_count = len(stage_info['containers'])
    ppc64le_ratio = float(ppc64le_count) / images_count
    assert ppc64le_ratio < 1 / 3.0


# Uncomment when session fixture works
# def test_pattern_file(staged_env):
#     config, stage_info = staged_env
    # Check patterns file
    # THe pattern file should be valid for use with grep
    # and should return all images matching suffixes
    suffixes = config['containers']['images-suffix']
    images_list = suffixes + [
        "jenkins",
        "zuul",
        "opendev",
        "devstack"
    ]
    images_list_text = "\n".join(sorted(images_list))

    images_suffix_text = "\n".join(sorted(suffixes))
    images_suffix_text += "\n"
    images_list_fd, images_list_path = tempfile.mkstemp()
    with open(images_list_path, "w") as ilp:
        ilp.write(images_list_text)
    os.close(images_list_fd)
    command = "grep -f {} {}".format(config['containers']['pattern_file_path'],
                                     images_list_path)
    output = subprocess.check_output(command.split()).decode("utf-8")
    os.unlink(images_list_path)
    assert output == images_suffix_text


# Uncomment when session fixture works
# def test_overcloud_images(staged_env):
#     config, stage_info = staged_env
    # Check images subtree, all full hases should be there
    overcloud_images_path = config['overcloud_images']['base_dir']
    distro_path = "{}{}".format(config['distro'], config['distro_version'])
    base_path = os.path.join(
        overcloud_images_path,
        distro_path,
        config['release'],
        'rdo_trunk',
    )
    # Check stage_info has the requred attributes
    overcloud_images = stage_info['overcloud_images']
    attributes = [
        'user',
        'key_path',
        'base_dir'
    ]
    for attribute in attributes:
        assert attribute in overcloud_images
    check_paths = []
    existing_paths = []
    for commit in stage_info['commits']:
        # check commit attributes are there
        assert 'commit_hash' in commit
        assert 'distro_hash' in commit
        assert 'full_hash' in commit
        full_hash = commit['full_hash']
        hash_path = os.path.join(base_path, full_hash)
        check_paths.append(hash_path)
        # We don't block at the first path found, I want to see all
        # the missing paths
        try:
            os.stat(hash_path)
            existing_paths.append(hash_path)
        except OSError:
            pass

    assert check_paths == existing_paths

    # check if we have a leaf with the symbolic link
    # and the dir linked exists
    promotion_name = stage_info['promotions']['currently_promoted']['name']
    promotion_link = os.path.join(base_path, promotion_name)
    promotion_target = os.readlink(promotion_link)
    # The fist commit is "the current promotion link"
    sample_path = os.path.join(base_path, stage_info['commits'][0]['full_hash'])
    assert promotion_target == sample_path
