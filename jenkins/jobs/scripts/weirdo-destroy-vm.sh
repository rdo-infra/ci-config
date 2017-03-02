#!/bin/bash
set -ex
WORKSPACE=${WORKSPACE:-/tmp}
JOB_NAME=${JOB_NAME:-rdo-ci}
BUILD_NUMBER=${BUILD_NUMBER:-000}
ANSIBLE_HOSTS=${ANSIBLE_HOSTS:-$WORKSPACE/hosts}
CLOUD_CONFIG=${CLOUD_CONFIG:-~/.config/openstack/clouds.yaml}

# Ansible config
CLOUD=${CLOUD:-trystack-temp}
NAME="${JOB_NAME}-${BUILD_NUMBER}"
TIMEOUT="120"
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
pip install ansible==2.2.1.0 ara shade

ara_location=$(python -c "import os,ara; print(os.path.dirname(ara.__file__))")
export ANSIBLE_HOST_KEY_CHECKING=False
export ANSIBLE_CALLBACK_PLUGINS="${ara_location}/plugins/callbacks"
export ARA_DATABASE="sqlite:///${WORKSPACE}/${JOB_NAME}.sqlite"

cat <<EOF >destroy-vm.yml
- name: Validate cloud authentication
  hosts: localhost
  gather_facts: false
  tasks:
    - name: Validate cloud authentication
      os_auth:
        cloud: "${CLOUD}"
      no_log: "yes"

- name: Collect logs
  hosts: logserver
  gather_facts: false
  tasks:
    - block:
        - name: Look up job virtual machine
          set_fact:
            vm: "{{ lookup('file', '${VM_INFO}') | from_json }}"

        - name: Create log destination directory
          file:
            path: "/var/www/html/{{ vm.openstack.metadata.job_name }}/{{ vm.openstack.metadata.build_number }}"
            state: "directory"
            recurse: "yes"

        # Synchronize doesn't prefix the username to the dest when using delegate_to
        # https://github.com/ansible/ansible/issues/16215
#        - name: Upload logs
#          synchronize:
#            recursive: "yes"
#            src: "/var/log/weirdo"
#            dest: "/var/www/html/{{ vm.openstack.metadata.job_name }}/{{ vm.openstack.metadata.build_number }}"
#          delegate_to: "{{ item }}"
#          with_items: "{{ groups['openstack_nodes'] }}"
#          ignore_errors: "yes"

        - name: Upload logs
          vars:
            ssh_opts: "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"
            src: "/var/log/weirdo/./"
            host: "{{ ansible_user }}@{{ inventory_hostname }}"
            path: "/var/www/html/{{ vm.openstack.metadata.job_name }}/{{ vm.openstack.metadata.build_number }}"
          shell: |
            rsync -e "{{ ssh_opts }}" -avzR {{ src }} {{ host }}:{{ path }}
          delegate_to: "{{ item }}"
          with_items: "{{ groups['openstack_nodes'] }}"
          ignore_errors: "yes"

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
            timeout: "${TIMEOUT}"
            wait: "yes"
EOF

ansible-playbook -i "${ANSIBLE_HOSTS}" destroy-vm.yml

# Generate and upload ARA report
ara generate html "${WORKSPACE}/ara"
cat <<EOF >ara.yml
- name: Upload ARA report
  hosts: logserver
  gather_facts: false
  tasks:
    - name: Look up job virtual machine
      set_fact:
        vm: "{{ lookup('file', '${VM_INFO}') | from_json }}"

    - name: Upload ARA report
      synchronize:
        src: "${WORKSPACE}/ara"
        dest: "/var/www/html/{{ vm.openstack.metadata.job_name }}/{{ vm.openstack.metadata.build_number }}/"
EOF

ansible-playbook -i "${ANSIBLE_HOSTS}" ara.yml

deactivate
popd
