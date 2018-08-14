#!/bin/bash -x

#Activate virtualenv
source ~/promoter_venv/bin/activate

while true; do

    #fetch the latest ci-config
    cd ~/ci-config; git pull >/dev/null

    #fetch the latest dlrnapi_client and dependencies
    pip install -U -r ~/ci-config/ci-scripts/dlrnapi_promoter/requirements.txt

    # Source secrets
    source ~/registry_secret
    source ~/dlrnapi_secret

    # promoter script for the master branch
    /usr/bin/timeout --preserve-status -k 120m 115m python ~/ci-config/ci-scripts/dlrnapi_promoter/dlrnapi_promoter.py ~/ci-config/ci-scripts/dlrnapi_promoter/config/master.ini

    # promoter script for the pike branch
    /usr/bin/timeout --preserve-status -k 120m 115m python ~/ci-config/ci-scripts/dlrnapi_promoter/dlrnapi_promoter.py ~/ci-config/ci-scripts/dlrnapi_promoter/config/pike.ini

    # promoter script for the ocata branch
    /usr/bin/timeout --preserve-status -k 120m 115m python ~/ci-config/ci-scripts/dlrnapi_promoter/dlrnapi_promoter.py ~/ci-config/ci-scripts/dlrnapi_promoter/config/ocata.ini

    # promoter script for the queens branch
    /usr/bin/timeout --preserve-status -k 120m 115m python ~/ci-config/ci-scripts/dlrnapi_promoter/dlrnapi_promoter.py ~/ci-config/ci-scripts/dlrnapi_promoter/config/queens.ini

    # promoter script for the rocky branch
    /usr/bin/timeout --preserve-status -k 120m 115m python ~/ci-config/ci-scripts/dlrnapi_promoter/dlrnapi_promoter.py ~/ci-config/ci-scripts/dlrnapi_promoter/config/rocky.ini

    # Sleep 10 minutes
    sleep 600
done
