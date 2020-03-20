#!/bin/bash

# systemd service for calling dlrn-promoter in a loop
# fetch latest config, install, call promoter, sleep
# keep this systemd service minimum

# https://github.com/pypa/pip/issues/6207
export PYTHONWARNINGS=ignore:Please.upgrade::pip._internal.cli.base_command

# Activate virtualenv
source ~/promoter_venv/bin/activate

while true; do

    # fetch the latest ci-config
    cd ~/ci-config; git reset --hard origin/master && git pull >/dev/null

    # fetch the latest dlrnapi_client and dependencies
    pip install -q -U -r ~/ci-config/ci-scripts/dlrnapi_promoter/requirements.txt

    # call dlrn-promoter.sh for multiple releases/distros
    /bin/bash -x ~/ci-config/ci-scripts/dlrnapi_promoter/dlrn-promoter.sh

    # Sleep 10 minutes
    sleep 600

done
