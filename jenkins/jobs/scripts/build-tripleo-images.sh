#!/bin/bash

# Install dependencies
sudo yum -y install git python-pip
sudo pip install ansible

export RELEASE=${1:-"master"}
export CPU_ARCH=${2:-"x86_64"}
export CICO_FLAVOR=${3:-"small"}

git clone https://github.com/rdo-infra/ci-config

pushd ci-config 
    bash -xe ci-scripts/tripleo-upstream/build-tripleo-images.sh
popd
