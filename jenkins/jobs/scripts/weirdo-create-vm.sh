#!/bin/bash
set -ex
WORKSPACE=${WORKSPACE:-/tmp}
JOB_NAME=${JOB_NAME:-rdo-ci}
BUILD_NUMBER=${BUILD_NUMBER:-000}
ANSIBLE_HOSTS=${ANSIBLE_HOSTS:-$WORKSPACE/hosts}
CLOUD_CONFIG=${CLOUD_CONFIG:-~/.config/openstack/clouds.yaml}
LOGSERVER="logs.rdoproject.org ansible_user=uploader"

# Ansible config
CLOUD=${CLOUD:-trystack-temp}
NAME="${JOB_NAME}-${BUILD_NUMBER}"
IMAGE="rdo-cico-weirdo-template"
KEY_NAME="cico"
TIMEOUT="120"
FLAVOR="m1.large"
VM_INFO="${WORKSPACE}/vminfo.json"

if [ ! -f "${CLOUD_CONFIG}" ]; then
    echo "Configuration file does not exist: ${CLOUD_CONFIG}"
    exit 1
fi

pushd $WORKSPACE

# Install dependencies
[[ ! -d provision_venv ]] && virtualenv provision_venv
source provision_venv/bin/activate
pip install ansible==2.2.1.0 ara shade

ara_location=$(python -c "import os,ara; print(os.path.dirname(ara.__file__))")
export ANSIBLE_HOST_KEY_CHECKING=False
export ANSIBLE_CALLBACK_PLUGINS="${ara_location}/plugins/callbacks"
export ARA_DATABASE="sqlite:///${WORKSPACE}/${NAME}.sqlite"

# Write the header of the hosts file
cat << EOF > ${ANSIBLE_HOSTS}
[logserver]
${LOGSERVER}

[openstack_nodes]
EOF

cat <<EOF >create-vm.yml
- name: Create job virtual machine
  hosts: localhost
  gather_facts: false
  tasks:
    - block:
        - name: Validate cloud authentication
          os_auth:
            cloud: "${CLOUD}"

        - name: Create job virtual machine
          os_server:
            state: "present"
            cloud: "${CLOUD}"
            name: "${NAME}"
            image: "${IMAGE}"
            key_name: "${KEY_NAME}"
            timeout: "${TIMEOUT}"
            flavor: "${FLAVOR}"
            wait: "yes"
            meta:
              hostname: "${NAME}"
              job_name: "${JOB_NAME}"
              build_number: "${BUILD_NUMBER}"
          register: vm

        - name: Dump complete virtual machine info
          vars:
            ansible_python_interpreter: "/usr/bin/python"
          copy:
            content: "{{ vm | to_nice_json }}"
            dest: "${VM_INFO}"

        - name: Wait until server is up and runnning
          local_action:
            module: "wait_for"
            port: "22"
            host: "{{ vm.openstack.accessIPv4 }}"
            search_regex: "OpenSSH"
            delay: "10"

        - name: Write inventory
          vars:
            ansible_python_interpreter: "/usr/bin/python"
          lineinfile:
            dest: "${ANSIBLE_HOSTS}"
            line: >-
              {{ vm.openstack.name }}
              ansible_host={{ vm.openstack.accessIPv4 }}
              ansible_user=centos
              ansible_become=yes
              ansible_become_user=root
EOF

ansible-playbook -i 'localhost' create-vm.yml

# Test VM connectivity
ansible -i ${ANSIBLE_HOSTS} openstack_nodes -m ping

deactivate
popd
