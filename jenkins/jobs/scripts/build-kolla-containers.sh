#!/bin/bash

# Install dependencies
sudo yum -y install git python-pip
sudo pip install ansible

export RELEASE=${1:-"master"}
export CPU_ARCH=${2:-"x86_64"}

git clone https://github.com/review.rdoproject.org-config

pushd review.rdoproject.org-config
    bash -xe ci-scripts/tripleo-upstream/build-containers-images.sh
popd
