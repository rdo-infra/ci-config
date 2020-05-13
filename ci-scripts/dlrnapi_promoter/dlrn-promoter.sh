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
LOG_LEVEL="INFO"
STAGING_DIR=""

DEFAULT_RELEASES=( "CentOS-8/master" "CentOS-8/ussuri" \
                   "CentOS-7/train" "CentOS-7/stein" \
                   "CentOS-7/rocky" "CentOS-7/queens" \
                   "RedHat-8/master" "CentOS-8/train" )
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
        STAGING_DIR="staging/"
        export IMAGE_SERVER_USER_HOST="foo@localhost"
        ;;
    h)
        usage
        exit 0
        ;;
    esac
done

RELEASES=("${TEST_RELEASE:-${DEFAULT_RELEASES[@]}}")
declare -p RELEASES

DIR=$(dirname $0)

for r in "${RELEASES[@]}"; do
    /usr/bin/timeout --preserve-status -k $KILLTIME $TIMEOUT \
        python $DIR/dlrnapi_promoter.py --log-level ${LOG_LEVEL} --config-file ${STAGING_DIR}${r}.ini promote-all
done
