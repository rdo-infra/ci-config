#!/bin/bash
cat <<EOF > /tmp/update_hosts
[grafana]
localhost
EOF
CUR_DIR=$(dirname ${BASH_SOURCE[0]:-$0})
export ANSIBLE_ROLES_PATH=$ANSIBLE_ROLES_PATH:$CUR_DIR
export ANSIBLE_HOST_KEY_CHECKING=False
ansible-playbook -i /tmp/update_hosts $CUR_DIR/setup_metrics_system.yml -e ansible_user=$USER -vv
