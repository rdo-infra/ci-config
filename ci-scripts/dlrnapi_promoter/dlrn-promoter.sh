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

RELEASES=( "CentOS-7/master" "CentOS-7/stein" "CentOS-7/rocky" \
           "CentOS-7/queens" "RedHat-8/master" )

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
      RELEASES=( "CentOS-7/staging" )
      export IMAGE_SERVER_USER_HOST="test@localhost"
      ;;
    h)
      usage
      exit 0
      ;;
    esac
done

for r in "${RELEASES[@]}"; do
#    /usr/bin/timeout --preserve-status -k $KILLTIME $TIMEOUT \
#        python ~/ci-config/ci-scripts/dlrnapi_promoter/dlrnapi_promoter.py \
#            ~/ci-config/ci-scripts/dlrnapi_promoter/config/${r}.ini
    echo "/usr/bin/timeout --preserve-status -k $KILLTIME $TIMEOUT \
        python ~/ci-config/ci-scripts/dlrnapi_promoter/dlrnapi_promoter.py \
            ~/ci-config/ci-scripts/dlrnapi_promoter/config/${r}.ini"
done

