#!/usr/bin/env /bin/bash

# test

usage(){
    echo "$0 Usage: $ dlrn-promoter.sh [-t 115m] [-k 120m] [-s] [-h]"
}

# Source secrets
source ~/registry_secret
source ~/dlrnapi_secret
# Promoter env
source ~/promoter_env
set -x

TIMEOUT=115m
KILLTIME=120m
STAGING_DIR=""
PROMOTER_CONFIG_ROOT="${PROMOTER_CONFIG_ROOT:=staging}"
PROMOTER_TYPE="${PROMOTER_TYPE:=upstream}"

if [[ $PROMOTER_TYPE == "upstream" ]]; then
    DEFAULT_RELEASES=( "CentOS-8/wallaby" \
                       "CentOS-8/victoria" "CentOS-8/ussuri" \
                       "CentOS-8/train" "CentOS-7/train" \
                       "CentOS-9/master" "CentOS-9/wallaby" )
else
    DEFAULT_RELEASES=( "RedHat-8/rhos-16.2" "RedHat-8/rhos-17" \
                       "RedHat-9/rhos-17" )
fi

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
        LOG_LEVEL="${LOG_LEVEL}"
        STAGING_DIR="staging/"
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

source ~/${PROMOTER_VENV:-promoter_venv}/bin/activate

for r in "${RELEASES[@]}"; do
    /usr/bin/timeout --preserve-status -k $KILLTIME $TIMEOUT \
        python3 $DIR/dlrnapi_promoter.py --log-level ${LOG_LEVEL} --config-root $PROMOTER_CONFIG_ROOT \
            --release-config ${r}.yaml promote-all
    # After the promoter has cycled through each release
    # run an exhaustive cleanup of the local containers.
    # This will prevent the systems from running out of space
    docker system prune -a -f
done
