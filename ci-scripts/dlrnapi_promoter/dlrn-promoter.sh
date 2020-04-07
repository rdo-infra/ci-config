#!/usr/bin/env /bin/bash

# test

usage(){
    echo "$0 Usage: $ dlrn-promoter.sh [-t 115m] [-k 120m] [-s] [-h]"
}

# Source secrets
source ~/registry_secret
source ~/dlrnapi_secret
set -x

TIMEOUT=115m
KILLTIME=120m
SCRIPT_DIR=$(dirname $0)
LOG_LEVEL="INFO"
CONFIG_ROOT="${SCRIPT_DIR}/config/"

DEFAULT_RELEASES=( "CentOS-7/master" "CentOS-7/train" \
                    "CentOS-7/stein" "CentOS-7/rocky" \
                    "CentOS-7/queens" "RedHat-8/master" \
                    "RedHat-8/train" )
declare -p DEFAULT_RELEASES


while getopts "t:k:sh" arg; do
    case $arg in
    t)
        TIMEOUT="${OPTARG}"
        ;;
    k)
        KILLTIME="${OPTARG}"
        ;;
    s)
        echo "Staging promoter mode enabled"
        LOG_LEVEL="DEBUG"
        CONFIG_ROOT="${SCRIPT_DIR}/stage_config/"
        ;;
    h)
        usage
        exit 0
        ;;
    esac
done

RELEASES=("${TEST_RELEASE:-${DEFAULT_RELEASES[@]}}")
declare -p RELEASES


for r in "${RELEASES[@]}"; do
    /usr/bin/timeout --preserve-status -k $KILLTIME $TIMEOUT \
        python ${SCRIPT_DIR}/dlrnapi_promoter.py \
         --log-level ${LOG_LEVEL} \
         --config-root ${CONFIG_ROOT} \
         --config-file ${r}.ini
         promote-all
done
