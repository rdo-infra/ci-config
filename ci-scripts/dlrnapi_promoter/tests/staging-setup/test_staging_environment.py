"""
This test is launched as part of the existing tox command

It tests that the staging environemnt provisioner is doing a correct
job by looking mainly at its output: the file, the directory structure, the
list of containers created.

Uses standard pytest fixture as a setup/teardown method
"""
import docker
import os
import pytest
import tempfile
import yaml

from staging_environment import StagedEnvironment, load_config


@pytest.fixture()
def source_image():

    client = docker.DockerClient(version="1.25")
    config = load_config(db_filepath="/tmp/sqlite-test.db")
    temp_dir = tempfile.mkdtemp()
    with open(os.path.join(temp_dir, "nothing"), "w"):
        pass
    with open(os.path.join(temp_dir, "Dockerfile"), "w") as dockerfile:
        dockerfile.write("FROM scratch\nCOPY nothing /\n")
    build_tag = config["containers"]["source_image"]
    image, _ = client.images.build(path=temp_dir, tag=build_tag)

    yield image

    client.images.remove(image.id, force=True)


@pytest.fixture()
def staged_env(source_image):
    """
    Fixture that runs the staging environment provisioner, yields the files
    produced and cleans up after
    """

    config = load_config(db_filepath="/tmp/sqlite-test.db")
    staged_env = StagedEnvironment(config, env_id="12345")
    staged_env.setup()

    root_dir = config['root-dir']
    # Meta file is neede for environment cleanup
    meta_file = os.path.join(root_dir, "meta.yaml")
    # Overcloud yaml file to pass to container push
    # format base/distro/full_hash/file
    overcloud_container_yaml_file = os.path.join(
        root_dir,
        "overcloud_containers_yaml/redhat8/1c67b1ab8c6fe273d4e175a14f0df5d3cb"
        "bd0edc_8170b868/overcloud_containers.yaml.j2")
    with open(meta_file) as mf:
        meta = mf.read()
    with open(overcloud_container_yaml_file) as of:
        overcloud_container_yaml = of.read()

    os.chdir(root_dir)
    tree = []
    for r, d, f in sorted(os.walk(".")):
        i = (r, sorted(d), sorted(f))

        tree.append(i)
    tree_yaml = yaml.safe_dump(tree)

    yield meta, overcloud_container_yaml, tree_yaml

    os.unlink("/tmp/sqlite-test.db")
    staged_env.teardown()


def test_samples(staged_env):
    """
    This test loads all the sample files, gets the files produced by the
    staging environment provision fixture and compares them
    (TODO) Optimize the file load and comparison with loops
    """

    base_path = os.path.dirname(os.path.abspath(__file__))
    meta_sample_file = os.path.join(base_path, "samples/meta.yaml")
    overcloud_yaml_sample_file = os.path.join(
        base_path, "samples/overcloud_containers.txt")
    tree_sample_file = os.path.join(base_path, "samples/tree.yaml")
    with open(meta_sample_file) as mf:
        meta_sample = mf.read()
    with open(tree_sample_file) as tf:
        tree_sample = tf.read()
    with open(overcloud_yaml_sample_file) as of:
        overcloud_yaml_sample = of.read()

#    image = source_image

    meta, overcloud_container_yaml, tree_yaml = staged_env

    assert meta == meta_sample
    assert overcloud_container_yaml == overcloud_yaml_sample
    assert tree_yaml == tree_sample
    # tree_sample_file = os.path.join(base_path, "samples/tree.txt")
    # with open(tree_sample_file) as tf:
    #    tree_sample = tf.read()
