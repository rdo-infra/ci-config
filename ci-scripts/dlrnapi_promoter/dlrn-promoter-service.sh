#!/bin/bash -x

#systemd service for calling dlrn-promoter in a loop
#fetch latest config, install, call promoter, sleep
#keep this systemd service minimum

#Activate virtualenv
source ~/promoter_venv/bin/activate

while true; do

    #fetch the latest ci-config
    #TODO(rfolco): convert this in a condition in j2 template,
    # skip if setup_staging is true
    #cd ~/ci-config; git reset --hard origin/master && git pull >/dev/null

    #fetch the latest dlrnapi_client and dependencies
    #TODO(rfolco): convert this in a condition in j2 template,
    # skip if setup_staging is true
    #pip install -U -r ~/ci-config/ci-scripts/dlrnapi_promoter/requirements.txt

    # call dlrn-promoter.sh for multiple releases/distros
    /bin/bash ~/ci-config/ci-scripts/dlrnapi_promoter/dlrn-promoter.sh

    # Sleep 10 minutes
    sleep 600
done
