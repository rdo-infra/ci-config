#!/bin/bash
# CI test that does an upgrade of a full oooq deployment.
# Use the major_upgrade flag to switch between major and minor upgrade
# Usage: upgrade-ovb.sh \
#        <release> \
#        <build_system> \
#        <config> \
#        <job_type> \
#        <major_upgrade>  \
#        <target_upgrade_version> \
#        <upgrade_delorean_hash> \
#        <hw-env-dir> \
#        <network-isolation> \
#        <ovb-settings-file> \
#        <ovb-creds-file> \
#        <playbook>

set -eux

RELEASE=$1
BUILD_SYS=$2
CONFIG=$3
JOB_TYPE=$4
MAJOR_UPGRADE=$5
TARGET_VERSION=$6
UPGRADE_DELOREAN_HASH=$7
HW_ENV_DIR=$8
NETWORK_ISOLATION=$9
OVB_SETTINGS_FILE=${10}
OVB_CREDS_FILE=${11}
PLAYBOOK=${12}

if [ "$JOB_TYPE" = "gate" ] || \
   [ "$JOB_TYPE" = "periodic" ] || \
   [ "$JOB_TYPE" = "dlrn-gate" ]; then
    unset REL_TYPE
    if [ "$RELEASE" = "master-tripleo-ci" ]; then
        # we don't have a local mirror for the tripleo-ci images
        unset CI_ENV
    fi
elif [ "$JOB_TYPE" = "dlrn-gate-check" ]; then
    # setup a test patch to be built
    export ZUUL_HOST=review.openstack.org
    export ZUUL_CHANGES=openstack/tripleo-ui:master:refs/changes/25/422025/2
    unset REL_TYPE
    if [ "$RELEASE" = "master-tripleo-ci" ]; then
        # we don't have a local mirror for the tripleo-ci images
        unset CI_ENV
    fi
elif [ "$JOB_TYPE" = "promote" ]; then
    export REL_TYPE=$LOCATION
else
    echo "Job type must be one of the following:"
    echo " * gate - for gating changes on tripleo-quickstart or -extras"
    echo " * promote - for running promotion jobs"
    echo " * periodic - for running periodic jobs"
    echo " * dlrn-gate - for gating upstream changes"
    echo " * dlrn-gate-check - for gating upstream changes"
    exit 1
fi

# (trown) This is so that we ensure separate ssh sockets for
# concurrent jobs. Without this, two jobs running in parallel
# would try to use the same undercloud-stack socket.
socketdir=$(mktemp -d /tmp/sockXXXXXX)
export ANSIBLE_SSH_CONTROL_PATH=$socketdir/%%h-%%r

# Disabling until reviews in tripleo-quickstart are merged
# preparation steps to run with the gated roles
#if [ "$JOB_TYPE" = "gate" ] || [ "$JOB_TYPE" = "dlrn-gate-check" ]; then
#    bash quickstart.sh \
#        --working-dir $WORKSPACE/ \
#        --no-clone \
#        --bootstrap \
#        --playbook gate-quickstart.yml \
#        --release ${CI_ENV:+$CI_ENV/}$RELEASE${REL_TYPE:+-$REL_TYPE} \
#        $OPT_ADDITIONAL_PARAMETERS \
#        $VIRTHOST
#fi

# TODO: Add dlrn gate check

bash quickstart.sh \
    --working-dir $WORKSPACE/ \
    --no-clone \
    --bootstrap \
    --tags all \
    --teardown all \
    --config $WORKSPACE/$HW_ENV_DIR/network_configs/$NETWORK_ISOLATION/config_files/$CONFIG \
    --extra-vars @$OVB_SETTINGS_FILE \
    --extra-vars @$OVB_CREDS_FILE \
    --extra-vars @$WORKSPACE/$HW_ENV_DIR/network_configs/$NETWORK_ISOLATION/env_settings.yml \
    --playbook $PLAYBOOK \
    --release ${CI_ENV:+$CI_ENV/}$RELEASE${REL_TYPE:+-$REL_TYPE} \
    --extra-vars upgrade_delorean_hash=$UPGRADE_DELOREAN_HASH \
    --extra-vars major_upgrade=$MAJOR_UPGRADE \
    --extra-vars target_upgrade_version=$TARGET_VERSION \
localhost
