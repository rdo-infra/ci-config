#!/bin/bash

# Install pip from python packaging authority to avoid using epel
curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py"
sudo python get-pip.py

# Install dependencies
sudo yum -y install git
sudo pip install ansible

export RELEASE=${1:-"master"}
export CPU_ARCH=${2:-"x86_64"}
export CICO_FLAVOR=${3:-"small"}

git clone https://github.com/rdo-infra/review.rdoproject.org-config

pushd review.rdoproject.org-config
    bash -xe ci-scripts/tripleo-upstream/build-containers-images.sh
popd
