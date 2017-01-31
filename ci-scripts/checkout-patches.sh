#!/bin/bash
# We hopefully will not need to merge this, but this is just checking out the
# needed patches for the new image build role. It needs to happen before we
# get a node from cico so that the correct changes end up in the quickstart
# venv
set -eux

# TODO(trown): Actually merge needed patches for new image building role.
pushd tripleo-quickstart
git fetch https://git.openstack.org/openstack/tripleo-quickstart refs/changes/19/424319/2 && git checkout FETCH_HEAD
popd

pushd tripleo-quickstart-extras
git fetch https://git.openstack.org/openstack/tripleo-quickstart-extras refs/changes/36/414336/15 && git checkout FETCH_HEAD
popd

cp $WORKSPACE/tripleo-quickstart/requirements.txt $WORKSPACE/local-requires.txt
echo "file://$WORKSPACE/tripleo-quickstart-extras/#egg=tripleo-quickstart-extras" >> local-requires.txt

bash $WORKSPACE/tripleo-quickstart/quickstart.sh \
    --working-dir $WORKSPACE/.quickstart \
    --no-clone \
    --clean \
    --bootstrap \
    --requirements $WORKSPACE/local-requires.txt \
    --playbook noop.yml \
    localhost

