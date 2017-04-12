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

# (trown) This is so that we ensure separate ssh sockets for
# concurrent jobs. Without this, two jobs running in parallel
# would try to use the same undercloud-stack socket.
socketdir=$(mktemp -d /tmp/sockXXXXXX)
export ANSIBLE_SSH_CONTROL_PATH=$socketdir/%%h-%%r

bash tripleo-quickstart/quickstart.sh \
    --tags all \
    --config $WORKSPACE/.quickstart/config/general_config/build_images.yml \
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
        --config $WORKSPACE/.quickstart/config/general_config/build_images.yml \
        --working-dir $WORKSPACE/.quickstart \
        --release ${CI_ENV:+$CI_ENV/}$RELEASE \
        --extra-vars undercloud_image_url="file:///var/lib/oooq-images/undercloud.qcow2" \
        $VIRTHOST
fi
