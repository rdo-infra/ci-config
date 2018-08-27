#!/bin/bash

# Install dependencies
sudo yum -y install git ansible

git clone https://github.com/rdo-infra/ci-config

pushd ci-config
    export RELEASE="master"
    bash -xe ci-scripts/tripleo-upstream/build-containers-images.sh
popd
