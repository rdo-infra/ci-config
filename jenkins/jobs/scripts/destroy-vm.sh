#!/bin/bash
set -ex

if [[ -n "${properties}" ]]; then
    curl -s -O "${properties}"
    source "./$(basename ${properties})"
fi

WORKSPACE=${WORKSPACE:-/tmp}
JOB_NAME=${JOB_NAME:-rdo-ci}
JOB_NAME_SIMPLIFIED=$((sed 's/scenario//; s/weirdo-//') <<< $JOB_NAME)
BUILD_NUMBER=${BUILD_NUMBER:-001}
ANSIBLE_HOSTS=${ANSIBLE_HOSTS:-$WORKSPACE/hosts}
CLOUD_CONFIG=${CLOUD_CONFIG:-~/.config/openstack/clouds.yaml}
LOGSERVER="logserver.rdoproject.org ansible_user=loguser"

# Ansible config
CLOUD=${CLOUD:-rdo-cloud}
NAME="${JOB_NAME_SIMPLIFIED}-${BUILD_NUMBER}"
TIMEOUT=${TIMEOUT:-120}
VM_INFO="${WORKSPACE}/vminfo.json"

if [ ! -f "${CLOUD_CONFIG}" ]; then
    echo "ERROR: Configuration file does not exist: ${CLOUD_CONFIG}"
    exit 1
fi

if [ ! -f "${VM_INFO}" ]; then
    echo "WARNING: Virtual machine information does not exist: ${VM_INFO}"
fi

if [ ! -f "${ANSIBLE_HOSTS}" ]; then
    echo "WARNING: Ansible hosts file does not exist: ${ANSIBLE_HOSTS}"
    echo "WARNING: Creating an Ansible hosts file for log collection..."

    # Write the header of the hosts file
    cat << EOF > ${ANSIBLE_HOSTS}
[logserver]
${LOGSERVER}

[openstack_nodes]
EOF
fi

pushd $WORKSPACE

# Install dependencies
[[ ! -d provision_venv ]] && virtualenv provision_venv
source provision_venv/bin/activate
pip install -c https://raw.githubusercontent.com/openstack/requirements/stable/train/upper-constraints.txt ansible==2.5.2 'ara<1.0.0' shade 'cmd2<0.9.0' 'pyfakefs<4.0.0'

ara_location=$(python -c "import os,ara; print(os.path.dirname(ara.__file__))")
export ANSIBLE_HOST_KEY_CHECKING=False
export ANSIBLE_CALLBACK_PLUGINS="${ara_location}/plugins/callbacks"
export ARA_DATABASE="sqlite:///${WORKSPACE}/${JOB_NAME}.sqlite"

cat <<EOF >prep-logs.yml
- name: Collect logs
  hosts: logserver
  gather_facts: false
  tasks:
    - block:
        - name: Create log destination directory
          file:
            path: "/var/www/logs/ci.centos.org/${JOB_NAME}/${BUILD_NUMBER}"
            state: "directory"
            recurse: "yes"
EOF
ansible-playbook -i "${ANSIBLE_HOSTS}" prep-logs.yml

# TODO: Fix this log collection madness
cat <<EOF >logs.yml
- name: Collect logs
  hosts: logserver
  gather_facts: false
  tasks:
    - block:
        - name: Look up job virtual machine
          set_fact:
            vm: "{{ lookup('file', '${VM_INFO}') | from_json }}"
          no_log: yes

        # Synchronize doesn't prefix the username to the dest when using delegate_to
        # https://github.com/ansible/ansible/issues/16215
        - name: Pull weirdo logs from VM to logserver
          vars:
            ssh_opts: "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"
            src: "/var/log/weirdo/./"
            host: "{{ hostvars[item]['ansible_user'] }}@{{ vm.openstack.accessIPv4 }}"
            path: "/var/www/logs/ci.centos.org/${JOB_NAME}/${BUILD_NUMBER}"
          shell: |
            rsync -e "{{ ssh_opts }}" -avzR {{ host }}:{{ src }} {{ path }}
          with_items: "{{ groups['openstack_nodes'] }}"
          when: vm is defined

        - name: Pull kolla logs from VM to logserver
          vars:
            ssh_opts: "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"
            src: "/tmp/kolla/logs/./"
            host: "{{ hostvars[item]['ansible_user'] }}@{{ vm.openstack.accessIPv4 }}"
            path: "/var/www/logs/ci.centos.org/${JOB_NAME}/${BUILD_NUMBER}"
          shell: |
            rsync -e "{{ ssh_opts }}" -avzR {{ host }}:{{ src }} {{ path }}
          with_items: "{{ groups['openstack_nodes'] }}"
          when: vm is defined
      ignore_errors: "yes"
EOF

ansible-playbook -i "${ANSIBLE_HOSTS}" logs.yml

cat <<EOF >destroy-vm.yml
- name: Destroy job virtual machine
  hosts: localhost
  gather_facts: false
  tasks:
    - name: Validate cloud authentication
      os_auth:
        cloud: "${CLOUD}"
      no_log: "yes"

    # Be a bit resilient to failures by trying at least twice
    - block:
        - name: Destroy job virtual machine
          os_server:
            state: "absent"
            cloud: "${CLOUD}"
            name: "${NAME}"
            timeout: "${TIMEOUT}"
            delete_fip: True
            wait: "yes"
      rescue:
        - name: Handling virtual machine deletion failure
          debug:
            msg: "The virtual machine creation failed, trying again ..."

        - name: Destroy job virtual machine
          os_server:
            state: "absent"
            cloud: "${CLOUD}"
            name: "${NAME}"
            timeout: "${TIMEOUT}"
            delete_fip: True
            wait: "yes"
          ignore_errors: "yes"
EOF

ansible-playbook -i "${ANSIBLE_HOSTS}" destroy-vm.yml

# Recover console log, generate and upload ARA report
ara generate html "${WORKSPACE}/ara"

# Copy database (experimental)
mkdir ${WORKSPACE}/ara-database
cp ${WORKSPACE}/${JOB_NAME}.sqlite ${WORKSPACE}/ara-database/ansible.sqlite

cat <<EOF >wrap-up.yml
- name: Upload ARA report and console log
  hosts: logserver
  gather_facts: false
  tasks:
    - name: Fetch and gzip the console log
      vars:
        build_url: "{{ lookup('env', 'BUILD_URL') }}"
      shell: |
        curl "{{ build_url }}/consoleText" | gzip > ${WORKSPACE}/console.txt.gz
      args:
        creates: "${WORKSPACE}/console.txt.gz"
      ignore_errors: True
      register: console

    - name: Upload the console log
      synchronize:
        src: "${WORKSPACE}/console.txt.gz"
        dest: "/var/www/logs/ci.centos.org/${JOB_NAME}/${BUILD_NUMBER}/"
      when: console | succeeded

    - name: Upload ARA report
      synchronize:
        src: "${WORKSPACE}/ara"
        dest: "/var/www/logs/ci.centos.org/${JOB_NAME}/${BUILD_NUMBER}/"

    - name: Upload ARA database
      synchronize:
        src: "${WORKSPACE}/ara-database"
        dest: "/var/www/logs/ci.centos.org/${JOB_NAME}/${BUILD_NUMBER}/"
EOF

ansible-playbook -i "${ANSIBLE_HOSTS}" wrap-up.yml

deactivate
popd
