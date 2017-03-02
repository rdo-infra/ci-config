#!/bin/bash
set -ex
WORKSPACE=${WORKSPACE:-/tmp}
CLOUD_CONFIG=${CLOUD_CONFIG:-~/.config/openstack/clouds.yaml}

# Ansible config
CLOUD=${CLOUD:-trystack-temp}
VM_INFO="${WORKSPACE}/vminfo.json"

if [ ! -f "${CLOUD_CONFIG}" ]; then
    echo "Configuration file does not exist: ${CLOUD_CONFIG}"
    exit 1
fi

if [ ! -f "${VM_INFO}" ]; then
    echo "Virtual machine information does not exist: ${VM_INFO}"
    exit 1
fi

pushd $WORKSPACE

# Install dependencies
[[ ! -d provision_venv ]] && virtualenv provision_venv
source provision_venv/bin/activate
pip install ansible==2.2.1.0 shade

# Test authentication
ansible localhost -m os_auth -a "cloud=${CLOUD}" >/dev/null

cat <<EOF >destroy-vm.yml
- name: Destroy job virtual machine
  hosts: localhost
  gather_facts: false
  tasks:
    - block:
        - name: Look up job virtual machine
          set_fact:
            vm: "{{ lookup('file', '${VM_INFO}') | from_json }}"

        - name: Destroy job virtual machine
          os_server:
            state: "absent"
            cloud: "${CLOUD}"
            name: "{{ vm.openstack.id }}"
            timeout: 120
            wait: "yes"
EOF

ansible-playbook -i 'localhost' destroy-vm.yml

popd