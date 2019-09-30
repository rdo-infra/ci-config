"""
This test is launched as part of the existing tox command

It tests that the staging environment provisioner is doing a correct
job by looking mainly at its output: the stage file, the directory structure,
the list of containers created.

Uses standard pytest fixture as a setup/teardown method
"""
import docker
import fnmatch
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


@pytest.fixture()
def staged_env():
    """
    Fixture that runs the staging environment provisioner, yields the files
    produced and cleans up after
    """

    components = "registries, container-images, overcloud-images"
    config = load_config(components, db_filepath="/tmp/sqlite-test.db")
    config['stage-info-path'] = "/tmp/stage-info.yaml"
    staged_env = StagedEnvironment(config)
    staged_env.setup()

    yield config

    staged_env.teardown()


def test_samples(staged_env):
    """
    This test loads all the sample files, gets the files produced by the
    staging environment provision fixture and compares them
    (TODO) Optimize the file load and comparison with loops
    """

    docker_client = docker.from_env()

    config = staged_env

    with open(config['stage-info-path'], "r") as stage_info_path:
        stage_info = yaml.safe_load(stage_info_path)

    # TODO(gcerami) Check db injection (needs sqlite3 import)

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
            assert found
        # Check that the registries are up and running
        assert docker_client.containers.get(registry['name'])
        # TODO(gcerami) Check registries respond correctly
    all_reg = (stage_info['registries']['targets']
               + [stage_info['registries']['source']])
    for registry in all_reg:
        # Check needed attributes
        assert "host" in registry
        assert "name" in registry
        assert "namespace" in registry
        assert "username" in registry
        assert "password" in registry

    # Check that all decleare containers are realy pushed
    ppc64le_count = 0
    found = []
    source_registry = stage_info['registries']['source']['host']
    print(stage_info['containers'])
    for full_name in stage_info['containers']:
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

    # Check images subtree, all full hases should be there
    overcloud_images_path = os.path.join(config['root-dir'],
                                         config['overcloud_images_base_dir'])
    base_path = os.path.join(
        overcloud_images_path,
        config['distro'],
        config['release'],
        'rdo_trunk',
    )
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
