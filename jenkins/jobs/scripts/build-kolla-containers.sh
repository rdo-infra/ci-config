#!/bin/bash

# Install dependencies
sudo yum -y install git ansible

OPENSTACK_RELEASE=${1:-"master"}

git clone https://github.com/rdo-infra/ci-config

pushd ci-config
    export RELEASE=$OPENSTACK_RELEASE
    bash -xe ci-scripts/tripleo-upstream/build-containers-images.sh
popd
