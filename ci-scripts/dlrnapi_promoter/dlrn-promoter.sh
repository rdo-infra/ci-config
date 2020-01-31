#!/bin/bash -x

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

# To add when ready: "RedHat-8/train"
RELEASES=( "CentOS-7/master" "CentOS-7/train" "CentOS-7/stein" \
           "CentOS-7/rocky" "CentOS-7/queens" \
           "RedHat-8/master" "RedHat-8/train" )

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
        export IMAGE_SERVER_USER_HOST="foo@localhost"
        ;;
    h)
        usage
        exit 0
        ;;
    esac
done

if [[ ! -z $TEST_RELEASES ]]; then
    RELEASES=("${TEST_RELEASES[@]}")
fi

DIR=$(dirname $0)

for r in "${RELEASES[@]}"; do
    /usr/bin/timeout --preserve-status -k $KILLTIME $TIMEOUT \
        python $DIR/dlrnapi_promoter.py --log-level ${LOG_LEVEL} ${r}.ini
done
