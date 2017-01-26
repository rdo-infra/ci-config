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
WORKSPACE=${WORKSPACE:-"~/.quickstart"}

if [ "$JOB_TYPE" = "gate" ] || [ "$JOB_TYPE" = "periodic" ]; then
    dlrn_hash='current-passed-ci'
elif [ "$JOB_TYPE" = "promote" ]; then
    dlrn_hash=${delorean_current_hash:-"consistent"}
else
    echo "Job type must be one of gate, periodic, or promote"
    exit 1
fi

pushd $WORKSPACE

git clone https://github.com/openstack/tripleo-quickstart
git clone https://github.com/openstack/tripleo-quickstart-extras

cp tripleo-quickstart/requirements.txt $WORKSPACE/local-requires.txt
echo "file:///$WORKSPACE/tripleo-quickstart-extras/#egg=tripleo-quickstart-extras" >> local-requires.txt

bash tripleo-quickstart/quickstart.sh \
    --working-dir $WORKSPACE/ \
    --no-clone \
    --bootstrap \
    --requirements local-requires.txt \
    --playbook noop.yml \
    localhost

bash tripleo-quickstart/ci-scripts/get-node.sh

export VIRTHOST=$(head -n1 $WORKSPACE/virthost)
echo $VIRTHOST

# (trown) This is so that we ensure separate ssh sockets for
# concurrent jobs. Without this, two jobs running in parallel
# would try to use the same undercloud-stack socket.
socketdir=$(mktemp -d /tmp/sockXXXXXX)
export ANSIBLE_SSH_CONTROL_PATH=$socketdir/%%h-%%r

bash tripleo-quickstart.sh \
    --tags all \
    --config $WORKSPACE/config/general_config/$CONFIG.yml \
    --working-dir $WORKSPACE/ \
    --playbook build-image-v2.yml \
    --no-clone \
    --release ${CI_ENV:+$CI_ENV/}$RELEASE \
    $VIRTHOST

if [ "$JOB_TYPE" = "gate" ] || [ "$JOB_TYPE" = "periodic" ]; then
bash tripleo-quickstart/quickstart.sh \
    --tags all \
    --no-clone \
    --release centosci/master \
    --extra-vars undercloud_image_url="file:///var/lib/oooq-images/undercloud.qcow2" \
    $VIRTHOST
fi
