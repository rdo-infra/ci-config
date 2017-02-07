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
#        <hw-env-dir> \
#        <network-isolation> \
#        <ovb-settings-file> \
#        <ovb-creds-file>

set -eux

RELEASE=$1
BUILD_SYS=$2
CONFIG=$3
JOB_TYPE=$4
MAJOR_UPGRADE=$5
TARGET_VERSION=$6
HW_ENV_DIR=$7
NETWORK_ISOLATION=$8
OVB_SETTINGS_FILE=$9
OVB_CREDS_FILE=${10}

if [ "$JOB_TYPE" = "gate" ] || [ "$JOB_TYPE" = "periodic" ]; then
    unset REL_TYPE
elif [ "$JOB_TYPE" = "promote" ]; then
    REL_TYPE=$LOCATION
else
    echo "Job type must be one of gate, periodic, or promote"
    exit 1
fi

# (trown) This is so that we ensure separate ssh sockets for
# concurrent jobs. Without this, two jobs running in parallel
# would try to use the same undercloud-stack socket.
socketdir=$(mktemp -d /tmp/sockXXXXXX)
export ANSIBLE_SSH_CONTROL_PATH=$socketdir/%%h-%%r

### DO WE NEED THIS STEP? upgrade.sh does not include it
if [ "$JOB_TYPE" = "gate" ]; then
    bash quickstart.sh \
        --working-dir $WORKSPACE/ \
        --no-clone \
        --bootstrap \
        --playbook gate-quickstart.yml \
        --release ${CI_ENV:+$CI_ENV/}$RELEASE${REL_TYPE:+-$REL_TYPE} \
        $OPT_ADDITIONAL_PARAMETERS \
        localhost
fi

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
    --playbook upgrade-baremetal.yml \
    --release ${CI_ENV:+$CI_ENV/}$RELEASE${REL_TYPE:+-$REL_TYPE} \
    --extra-vars major_upgrade=$MAJOR_UPGRADE \
    --extra-vars target_upgrade_version=$TARGET_VERSION \
localhost

