set -ex
CICO_USER_DIR=${CICO_USER_DIR:-/root}
WORKSPACE=${WORKSPACE:-/tmp}
ANSIBLE_HOSTS=${ANSIBLE_HOSTS:-$WORKSPACE/hosts}
LOGSERVER="logs.rdoproject.org ansible_user=uploader"
SOURCE="${CICO_USER_DIR}/workspace/logs"
DESTINATION="/var/www/html/ci.centos.org/${JOB_NAME}/${BUILD_NUMBER}"
VENV="${WORKSPACE}/venv"

[[ ! -d "${VENV}" ]] && virtualenv "${VENV}"
source "${VENV}/bin/activate"

# Ensure that ansible is installed.
pip install ansible==2.5.8

# Add logserver to the ansible_hosts file
cat << EOF >> ${ANSIBLE_HOSTS}
[logserver]
${LOGSERVER}
EOF

pushd $WORKSPACE
mkdir -p $WORKSPACE/logs

cat << EOF > collect-logs.yaml
# Create a playbook to pull the logs down from our cico node
- name: Group together logs on cico node
  hosts: openstack_nodes
  gather_facts: no
  tasks:
   - shell: |
        mkdir -p ${CICO_USER_DIR}/workspace/logs

        pushd ${CICO_USER_DIR}/workspace
            cp *.log ./logs/
            cp *.conf ./logs/
        popd

- name: Collect logs from cico node
  hosts: openstack_nodes
  gather_facts: no
  tasks:
    - synchronize:
          mode: pull
          src: "${SOURCE}"
          dest: "${WORKSPACE}/logs/"

- name: Send logs to the log server
  hosts: logserver
  gather_facts: no
  tasks:
    - name: Create log destination directory
      file:
        path: "${DESTINATION}"
        state: directory
        recurse: yes

    - name: Upload logs to log server
      synchronize:
        src: "${WORKSPACE}/logs"
        dest: "${DESTINATION}/"
EOF

# Run the playbooks.
ansible-playbook -i "${ANSIBLE_HOSTS}" collect-logs.yaml

popd
