set -ex
CICO_USER_DIR=${CICO_USER_DIR:-/root}
WORKSPACE=${WORKSPACE:-/tmp}
ANSIBLE_HOSTS=${ANSIBLE_HOSTS:-$WORKSPACE/hosts}
CONTAINER_BUILD_LOG_DIR=${CONTAINER_LOG_DIR:-container-builds}
LOGSERVER="logserver.rdoproject.org ansible_user=loguser"
LOG_DISPLAY_URL="https://logserver.rdoproject.org/ci.centos.org/${JOB_NAME}/${BUILD_NUMBER}"
CI_CENTOS_URL="https://jenkins-cloudsig-ci.apps.ocp.ci.centos.org/job/${JOB_NAME}/${BUILD_NUMBER}"
SOURCE="${CICO_USER_DIR}/workspace/logs"
DESTINATION="/var/www/logs/ci.centos.org/${JOB_NAME}/${BUILD_NUMBER}"
VENV="${WORKSPACE}/venv"

[[ ! -d "${VENV}" ]] && virtualenv "${VENV}"
source "${VENV}/bin/activate"

# Ensure that ansible is installed.
pip install ansible==2.8.0

# Add logserver to the ansible_hosts file
cat << EOF >> ${ANSIBLE_HOSTS}
[logserver]
${LOGSERVER}
EOF

pushd $WORKSPACE
mkdir -p $WORKSPACE/logs

# Collect terminal output from centos-ci job regardless of job/cico status
curl -o $WORKSPACE/logs/consoleText.txt ${CI_CENTOS_URL}/consoleText || true

cat << EOF > collect-logs.yaml
# Create a playbook to pull the logs down from our cico node
- name: Group together logs on cico node
  hosts: openstack_nodes
  gather_facts: no
  tasks:
   - shell: |
        pushd ${CICO_USER_DIR}/workspace
            mkdir -p ./logs/${CONTAINER_BUILD_LOG_DIR}/
            cp *.log ./logs/ || true
            cp *.conf ./logs/ || true
            cp *.sh ./logs/ || true
            cp -r /tmp/${CONTAINER_BUILD_LOG_DIR}  ./logs/${CONTAINER_BUILD_LOG_DIR}/ || true
            chmod -R 755 ./logs
        popd

- name: Collect logs from cico node
  hosts: openstack_nodes
  gather_facts: no
  tasks:
    - synchronize:
          mode: pull
          src: "${SOURCE}"
          dest: "${WORKSPACE}/logs/"
          recursive: yes
          dirs: no

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
        recursive: yes
        dirs: no

    - shell: |
        echo "All collected logs are available at ${LOG_DISPLAY_URL}"
EOF


# We keep connecting onto the same hosts that are continuously reinstalled
export ANSIBLE_HOST_KEY_CHECKING=False

# Run the playbooks.
ansible-playbook --ssh-extra-args="-o UserKnownHostsFile=/dev/null" -vvv -i "${ANSIBLE_HOSTS}" collect-logs.yaml

popd
