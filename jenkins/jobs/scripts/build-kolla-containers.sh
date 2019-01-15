#!/bin/bash

# Install dependencies
sudo yum -y install gcc git python-devel python-setuptools libffi libffi-devel openssl openssl-devel
sudo easy_install pip
sudo pip install ansible

export RELEASE=${1:-"master"}
export CPU_ARCH=${2:-"x86_64"}
export CICO_FLAVOR=${3:-"small"}

git clone https://github.com/rdo-infra/review.rdoproject.org-config

pushd review.rdoproject.org-config
    bash -xe ci-scripts/tripleo-upstream/build-containers-images.sh
popd
