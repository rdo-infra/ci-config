#!/bin/bash
# CI test that builds images for both promote and gate jobs.
# For the promote jobs it uses the provided trunk repo hash and only builds
# an image.
# For the gate jobs it tests the current-passed-ci repo with a full deploy.
# Usage: images.sh <release> <config> <job_type>
set -eux

RELEASE=$1
CONFIG=$2
JOB_TYPE=$3
WORKSPACE=${WORKSPACE:-"~/"}

if [ "$JOB_TYPE" = "gate" ] || [ "$JOB_TYPE" = "periodic" ]; then
    dlrn_hash='current-passed-ci'
elif [ "$JOB_TYPE" = "promote" ]; then
    dlrn_hash=${delorean_current_hash:-"consistent"}
else
    echo "Job type must be one of gate, periodic, or promote"
    exit 1
fi

mkdir -p $WORKSPACE
pushd $WORKSPACE

# TODO(trown): Actually merge needed patches for new image building role.
[[ ! -e tripleo-quickstart ]] && git clone https://github.com/openstack/tripleo-quickstart
pushd tripleo-quickstart
git fetch https://git.openstack.org/openstack/tripleo-quickstart refs/changes/19/424319/1 && git checkout FETCH_HEAD
popd

[[ ! -e tripleo-quickstart-extras ]] && git clone https://github.com/openstack/tripleo-quickstart-extras
pushd tripleo-quickstart-extras
git fetch https://git.openstack.org/openstack/tripleo-quickstart-extras refs/changes/36/414336/5 && git checkout FETCH_HEAD
popd

cp tripleo-quickstart/requirements.txt $WORKSPACE/local-requires.txt
echo "file://$WORKSPACE/tripleo-quickstart-extras/#egg=tripleo-quickstart-extras" >> local-requires.txt

bash tripleo-quickstart/quickstart.sh \
    --working-dir $WORKSPACE/.quickstart \
    --no-clone \
    --clean \
    --bootstrap \
    --requirements $WORKSPACE/local-requires.txt \
    --playbook noop.yml \
    localhost

# Only run the get-node script if running in CI
if [ -v CI_ENV ]; then
    bash tripleo-quickstart/ci-scripts/get-node.sh

    export VIRTHOST=$(head -n1 $WORKSPACE/virthost)
    echo $VIRTHOST
fi

# (trown) This is so that we ensure separate ssh sockets for
# concurrent jobs. Without this, two jobs running in parallel
# would try to use the same undercloud-stack socket.
socketdir=$(mktemp -d /tmp/sockXXXXXX)
export ANSIBLE_SSH_CONTROL_PATH=$socketdir/%%h-%%r

bash tripleo-quickstart/quickstart.sh \
    --tags all \
    --config $WORKSPACE/.quickstart/config/general_config/$CONFIG.yml \
    -e dlrn_hash=$dlrn_hash \
    --working-dir $WORKSPACE/.quickstart \
    -e images_working_dir=/var/lib/oooq-images \
    --playbook build-images-v2.yml \
    --no-clone \
    --release ${CI_ENV:+$CI_ENV/}$RELEASE \
    $VIRTHOST

if [ "$JOB_TYPE" = "gate" ] || [ "$JOB_TYPE" = "periodic" ]; then
    bash tripleo-quickstart/quickstart.sh \
        --tags all \
        --no-clone \
        --config $WORKSPACE/.quickstart/config/general_config/$CONFIG.yml \
        --working-dir $WORKSPACE/.quickstart \
        --release ${CI_ENV:+$CI_ENV/}$RELEASE \
        --extra-vars undercloud_image_url="file:///var/lib/oooq-images/undercloud.qcow2" \
        $VIRTHOST
fi
