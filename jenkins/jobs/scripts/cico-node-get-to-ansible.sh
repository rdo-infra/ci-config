#!/bin/bash
# A script that provisions nodes and writes them to an Ansible inventory file
NODE_COUNT=${NODE_COUNT:-1}
ANSIBLE_HOSTS=${ANSIBLE_HOSTS:-$WORKSPACE/hosts}
SSID_FILE=${SSID_FILE:-$WORKSPACE/cico-ssid}
ANSIBLE_SSH_KEY=${ANSIBLE_SSH_KEY:-/home/rhos-ci/.ssh/id_rsa}

# Write the header of the hosts file
cat << EOF > ${HOST_FILE}
localhost ansible_connection=local

[openstack_nodes]
EOF

# Get nodes
# nodes=$(cico -q node get --count ${NODE_COUNT} --column hostname --column ip_address --column comment -f value)
nodes=$(cat /tmp/cico)

# Write nodes to inventory file and persist the SSID separately for simplicity
touch ${SSID_FILE}
IFS=$'\n'
for node in ${nodes}
do
    host=$(echo "${node}" |cut -f1 -d " ")
    address=$(echo "${node}" |cut -f2 -d " ")
    ssid=$(echo "${node}" |cut -f3 -d " ")

    line="${host} ansible_host=${address} ansible_user=root ansible_ssh_private_key_file=${ANSIBLE_SSH_KEY} cico_ssid=${ssid}"
    echo "${line}" >> ${HOST_FILE}

    # Write unique SSIDs to the SSID file
    if ! grep -q ${ssid} ${SSID_FILE}; then
        echo ${ssid} >> ${SSID_FILE}
    fi
done
