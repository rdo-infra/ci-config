#!/bin/bash -x

# Source secrets
source ~/registry_secret
source ~/dlrnapi_secret
set -x

TIMEOUT=115m
KILLTIME=120m

CENTOS7_RELEASES=( "master" "stein" "rocky" "queens" "ocata" "pike" )
FEDORA28_RELEASES=( "master" "stein")

# promoter script for centos 7
for r in "${CENTOS7_RELEASES[@]}"; do
    /usr/bin/timeout --preserve-status -k $KILLTIME $TIMEOUT \
        python ~/ci-config/ci-scripts/dlrnapi_promoter/dlrnapi_promoter.py \
            ~/ci-config/ci-scripts/dlrnapi_promoter/config/CentOS-7/${r}.ini
done

# promoter script for fedora 28
for r in "${FEDORA28_RELEASES[@]}"; do
    /usr/bin/timeout --preserve-status -k $KILLTIME $TIMEOUT \
        python ~/ci-config/ci-scripts/dlrnapi_promoter/dlrnapi_promoter.py \
            ~/ci-config/ci-scripts/dlrnapi_promoter/config/Fedora-28/${r}.ini
done

