#!/bin/bash
set -ex
WORKSPACE=${WORKSPACE:-/tmp}
JOB_NAME=${JOB_NAME:-rdo-ci}
BUILD_NUMBER=${BUILD_NUMBER:-001}
ANSIBLE_HOSTS=${ANSIBLE_HOSTS:-$WORKSPACE/hosts}
CLOUD_CONFIG=${CLOUD_CONFIG:-~/.config/openstack/clouds.yaml}
LOGSERVER="logs.rdoproject.org ansible_user=uploader"

# Ansible config
CLOUD=${CLOUD:-rdo-cloud}
NETWORK=${NETWORK:-private}
NAME="${JOB_NAME}-${BUILD_NUMBER}"
IMAGE=${IMAGE:-template-centos7-weirdo}
TIMEOUT=${TIMEOUT:-120}
FLAVOR=${FLAVOR:-rdo.m1.nodepool}
VM_INFO="${WORKSPACE}/vminfo.json"

if [ ! -f "${CLOUD_CONFIG}" ]; then
    echo "Configuration file does not exist: ${CLOUD_CONFIG}"
    exit 1
fi

pushd $WORKSPACE

# Install dependencies
[[ ! -d provision_venv ]] && virtualenv provision_venv
source provision_venv/bin/activate
pip install ansible==2.3.0.0 ara shade

ara_location=$(python -c "import os,ara; print(os.path.dirname(ara.__file__))")
export ANSIBLE_HOST_KEY_CHECKING=False
export ANSIBLE_CALLBACK_PLUGINS="${ara_location}/plugins/callbacks"
export ARA_DATABASE="sqlite:///${WORKSPACE}/${JOB_NAME}.sqlite"

# Write the header of the hosts file
cat << EOF > ${ANSIBLE_HOSTS}
[logserver]
${LOGSERVER}

[openstack_nodes]
EOF

cat <<EOF >cleanup-stale-vms.yml
- name: Cleanup stale VMs
  hosts: localhost
  gather_facts: false
  tasks:
    - name: Validate cloud authentication
      os_auth:
        cloud: "${CLOUD}"
    - name: Gather facts
      os_server_facts:
        cloud: "${CLOUD}"
    - block:
        - name: Delete VMs in ERROR state
          os_server:
            state: "absent"
            cloud: "${CLOUD}"
            name: "{{ item.name }}"
            timeout: "${TIMEOUT}"
            delete_fip: True
            wait: "yes"
          when: item.status == "ERROR"
          with_items:
            - "{{ openstack_servers }}"
      rescue:
        - name: Handling virtual machine deletion failure
          debug:
            msg: "The virtual machine cleanup failed, trying again ..."

        - name: Destroy job virtual machine
          os_server:
            state: "absent"
            cloud: "${CLOUD}"
            name: "{{ item.name }}"
            timeout: "${TIMEOUT}"
            delete_fip: True
            wait: "yes"
            ignore_errors: "yes"
          when: item.status == "ERROR"
          with_items:
            - "{{ openstack_servers }}"
EOF

ansible-playbook -i 'localhost' cleanup-stale-vms.yml

deactivate
popd
