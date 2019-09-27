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
import tempfile
import subprocess
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

    # Check that all decleare containers are realy pushed
    ppc64le_count = 0
    source_registry = stage_info['registries']['source']['host']
    for container in stage_info['containers']:
        if "_ppc64le" in container:
            ppc64le_count += 1
        remote_registry_data = docker_client.images.get_registry_data(
            "{}/{}".format(source_registry, container))
        assert remote_registry_data

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

    # Check images subtree
    # Just check if we have a leaf with the symbolic link
    # and the dir linked exists
    overcloud_images_path = os.path.join(config['root-dir'],
                                         config['overcloud_images_base_dir'])
    promotion_path = os.path.join(
        overcloud_images_path,
        config['distros'][0],
        config['release'],
        'rdo_trunk',
    )
    promotion_link = os.path.join(promotion_path, config['candidate_name'])
    promotion_target = os.readlink(promotion_link)

    # The fist commit is "the current promotion link"
    sample_path = os.path.join(promotion_path, stage_info['commits'][0])
    assert promotion_target == sample_path

    # This may check the entire subtree, but I'm not sure it's needed.
    matches = []
    for root, dirnames, filenames in os.walk(overcloud_images_path):
        for dirname in fnmatch.filter(dirnames, '*'):
            matches.append(os.path.join(root, dirname))
        for filename in fnmatch.filter(filenames, '*'):
            matches.append(os.path.join(root, filename))
