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

cat <<EOF >create-vm.yml
- name: Create job virtual machine
  hosts: localhost
  gather_facts: true
  vars:
    fmt: '%Y-%m-%dT%H:%M:%SZ'
  tasks:
    - name: Validate cloud authentication
      os_auth:
        cloud: "${CLOUD}"
    - name: Gather tenant facts
      os_server_facts:
        cloud: "${CLOUD}"
    - block:
        - name: Delete VMs in ERROR state or too old
          os_server:
            state: "absent"
            cloud: "${CLOUD}"
            name: "{{ item.name }}"
            timeout: "${TIMEOUT}"
            delete_fip: True
            wait: "yes"
          when: item.status == "ERROR" or ((ansible_date_time.iso8601|to_datetime(fmt)) - (item.created|to_datetime(fmt))).seconds > 21600
          with_items:
            - "{{ openstack_servers }}"
      rescue:
        - name: Handling virtual machine deletion failure
          debug:
            msg: "The stale VM cleanup failed, trying again ..."
        - name: Delete VMs in ERROR state or too old, take 2
          os_server:
            state: "absent"
            cloud: "${CLOUD}"
            name: "{{ item.name }}"
            timeout: "${TIMEOUT}"
            delete_fip: True
            wait: "yes"
            ignore_errors: "yes"
          when: item.status == "ERROR"  or ((ansible_date_time.iso8601|to_datetime(fmt)) - (item.created|to_datetime(fmt))).seconds > 21600
          with_items:
            - "{{ openstack_servers }}"

    # Be a bit resilient to failures by trying at least twice
    - block:
        - name: Create job virtual machine
          os_server:
            state: "present"
            cloud: "${CLOUD}"
            name: "${NAME}"
            image: "${IMAGE}"
            flavor: "${FLAVOR}"
            network: "${NETWORK}"
            reuse_ips: "no"
            timeout: "${TIMEOUT}"
            boot_from_volume: "yes"
            terminate_volume: "yes"
            volume_size: 80
            wait: "yes"
            meta:
              hostname: "${NAME}"
              job_name: "${JOB_NAME}"
              build_number: "${BUILD_NUMBER}"
          register: vm
      rescue:
        - name: Handling virtual machine creation failure
          debug:
            msg: "The virtual machine creation failed, trying again ..."

        - name: Create job virtual machine (second attempt)
          os_server:
            state: "present"
            cloud: "${CLOUD}"
            name: "${NAME}"
            image: "${IMAGE}"
            flavor: "${FLAVOR}"
            network: "${NETWORK}"
            reuse_ips: "no"
            timeout: "${TIMEOUT}"
            boot_from_volume: "yes"
            terminate_volume: "yes"
            volume_size: 100
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
