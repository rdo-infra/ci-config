#!/bin/bash
# Check that tenant credentials have been sourced
if [[ ! -v OS_AUTH_URL ]]; then
    echo "Tenant credentials are not sourced."
    exit 1;
fi
CUR_DIR=$(dirname ${BASH_SOURCE[0]:-$0})
ansible-playbook grafana-playbook.yml -e @$CUR_DIR/cloud_settings.yml -vv
