#!/bin/bash

# This script does a manual container push for a user specified hash.
# Use this in only in case you know what you are doing.

source ~/registry_secret
export SCRIPT_ROOT=/home/centos/ci-config

if [[ -z "$PROMOTE_NAME" ]]; then
    read -p "PROMOTE_NAME=" PROMOTE_NAME
fi
export PROMOTE_NAME

if [[ -z "$FULL_HASH" ]]; then
    read -p "FULL_HASH=" FULL_HASH
fi
export FULL_HASH

if [[ -z "$RELEASE" ]]; then
    read -p "RELEASE=" RELEASE
fi
export RELEASE

ansible-playbook -v container-push.yml
