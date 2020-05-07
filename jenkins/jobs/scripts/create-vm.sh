#!/bin/bash
set -ex
WORKSPACE=${WORKSPACE:-/tmp}
JOB_NAME=${JOB_NAME:-rdo-ci}
JOB_NAME_SIMPLIFIED=$((sed 's/scenario//; s/weirdo-//') <<< $JOB_NAME)
BUILD_NUMBER=${BUILD_NUMBER:-001}
ANSIBLE_HOSTS=${ANSIBLE_HOSTS:-$WORKSPACE/hosts}
CLOUD_CONFIG=${CLOUD_CONFIG:-~/.config/openstack/clouds.yaml}
LOGSERVER="logserver.rdoproject.org ansible_user=loguser"

# If a properties file is specified, it should overwrite and have priority over other parameters
if [[ -n "${properties}" ]]; then
    curl -s -O "${properties}"
    source "./$(basename ${properties})"
fi

# Ansible config
CLOUD=${CLOUD:-vexxhost}
NETWORK=${NETWORK:-private-network}
NAME="${JOB_NAME_SIMPLIFIED}-${BUILD_NUMBER}"
IMAGE=${IMAGE:-template-rdo-centos-7}
TIMEOUT=${TIMEOUT:-120}
FLAVOR=${FLAVOR:-nodepool-infra}
VM_INFO="${WORKSPACE}/vminfo.json"
ANSIBLE_PYTHON_INTERPRETER=${ANSIBLE_PYTHON_INTERPRETER:-/usr/bin/python}

if [ ! -f "${CLOUD_CONFIG}" ]; then
    echo "Configuration file does not exist: ${CLOUD_CONFIG}"
    exit 1
fi

pushd $WORKSPACE

# Install dependencies
[[ ! -d provision_venv ]] && virtualenv provision_venv
source provision_venv/bin/activate
pip install -c https://raw.githubusercontent.com/openstack/requirements/stable/train/upper-constraints.txt ansible==2.5.2 'ara<1.0.0' shade 'cmd2<0.9.0' 'pyfakefs<4.0.0'

# Is there a better way ?
git clone https://github.com/rdo-infra/ci-config
nodepool_image=$(python ci-config/jenkins/jobs/scripts/get-nodepool-image.py "${CLOUD}" --pattern "${IMAGE}")

ara_location=$(python -c "import os,ara; print(os.path.dirname(ara.__file__))")
export ANSIBLE_HOST_KEY_CHECKING=False
export ANSIBLE_CALLBACK_PLUGINS="${ara_location}/plugins/callbacks"
export ANSIBLE_GATHERING="implicit"
# Unreachable tasks may not be handled: https://github.com/ansible/ansible/issues/18287
export ANSIBLE_SSH_RETRIES=6
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
      no_log: yes

    - name: Gather tenant facts
      os_server_facts:
        cloud: "${CLOUD}"
      no_log: yes

    - block:
        - name: Delete VMs in ERROR state or too old
          os_server:
            state: "absent"
            cloud: "${CLOUD}"
            name: "{{ item.name }}"
            timeout: "${TIMEOUT}"
            delete_fip: True
            wait: "yes"
          no_log: yes
          when: item.status == "ERROR" or ((ansible_date_time.iso8601|to_datetime(fmt)) - (item.created|to_datetime(fmt))).days >= 1
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
          no_log: yes
          when: item.status == "ERROR" or ((ansible_date_time.iso8601|to_datetime(fmt)) - (item.created|to_datetime(fmt))).days >= 1
          with_items:
            - "{{ openstack_servers }}"

    # Be a bit resilient to failures by trying at least twice
    - block:
        - name: Create job virtual machine
          os_server:
            state: "present"
            cloud: "${CLOUD}"
            name: "${NAME}"
            image: "${nodepool_image}"
            flavor: "${FLAVOR}"
            network: "${NETWORK}"
            reuse_ips: "no"
            timeout: "${TIMEOUT}"
            config_drive: "yes"
            boot_from_volume: "no"
            wait: "yes"
            meta:
              hostname: "${NAME}"
              job_name: "${JOB_NAME}"
              build_number: "${BUILD_NUMBER}"
          no_log: yes
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
            image: "${nodepool_image}"
            flavor: "${FLAVOR}"
            network: "${NETWORK}"
            reuse_ips: "no"
            timeout: "${TIMEOUT}"
            config_drive: "yes"
            boot_from_volume: "no"
            wait: "yes"
            meta:
              hostname: "${NAME}"
              job_name: "${JOB_NAME}"
              build_number: "${BUILD_NUMBER}"
          no_log: yes
          register: vm

    - name: Dump complete virtual machine info
      vars:
        ansible_python_interpreter: "/usr/bin/python"
      copy:
        content: "{{ vm | to_nice_json }}"
        dest: "${VM_INFO}"
      no_log: yes

    - name: Wait until server is up and runnning
      local_action:
        module: "wait_for"
        port: "22"
        host: "{{ vm.openstack.accessIPv4 }}"
        search_regex: "OpenSSH"
        delay: "30"

    - name: Add server to inventory
      add_host:
        hostname: "{{ vm.openstack.name }}"
        ansible_ssh_host: "{{ vm.openstack.accessIPv4 }}"
        ansible_user: "jenkins"
        ansible_become: "yes"
        ansible_become_user: "root"
        ansible_python_interpreter: "${ANSIBLE_PYTHON_INTERPRETER}"

    - name: Ensure the server is reachable
      ping:
      register: ping
      until: ping | success
      retries: 6
      delay: 5
      delegate_to: "{{ vm.openstack.name }}"

    - name: Write inventory
      vars:
        ansible_python_interpreter: "/usr/bin/python"
      lineinfile:
        dest: "${ANSIBLE_HOSTS}"
        line: >-
          {{ vm.openstack.name }}
          ansible_host={{ vm.openstack.accessIPv4 }}
          ansible_user=jenkins
          ansible_become=yes
          ansible_become_user=root
          ansible_python_interpreter="${ANSIBLE_PYTHON_INTERPRETER}"
EOF

ansible-playbook -i 'localhost' create-vm.yml

deactivate
popd
