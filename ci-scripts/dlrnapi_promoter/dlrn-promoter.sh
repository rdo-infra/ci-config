#!/bin/bash -x

# Source secrets
source ~/registry_secret
source ~/dlrnapi_secret
set -x

TIMEOUT=115m
KILLTIME=120m

RELEASES=( "CentOS-7/master" "CentOS-7/stein" "CentOS-7/rocky" \
           "CentOS-7/queens" "CentOS-7/ocata" "RedHat-8/master" )

for r in "${RELEASES[@]}"; do
    /usr/bin/timeout --preserve-status -k $KILLTIME $TIMEOUT \
        python ~/ci-config/ci-scripts/dlrnapi_promoter/dlrnapi_promoter.py \
            ~/ci-config/ci-scripts/dlrnapi_promoter/config/${r}.ini
done

