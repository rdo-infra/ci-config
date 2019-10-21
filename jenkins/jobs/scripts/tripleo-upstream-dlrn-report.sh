set -ex
CICO_USER_DIR=${CICO_USER_DIR:-/root}
WORKSPACE=${WORKSPACE:-/tmp}
ANSIBLE_HOSTS=${ANSIBLE_HOSTS:-$WORKSPACE/hosts}
VENV="${WORKSPACE}/venv"
RDO_CONFIG_DIR="${RDO_CONFIG_DIR:-src/rdo-infra/review.rdoproject.org-config}"

[[ ! -d "${VENV}" ]] && virtualenv "${VENV}"
source "${VENV}/bin/activate"

# Ensure that ansible is installed.
pip install ansible==2.5.8

pushd $WORKSPACE

cat << EOF > delorean-report.yaml
# Create a playbook to report results to delorean
- name: Report results to delorean
  hosts: openstack_nodes
  gather_facts: no
  tasks:
   - shell: |
        export WORKSPACE=${CICO_USER_DIR}/workspace
        export TOCI_JOBTYPE="${JOB_NAME}"
        export LOG_HOST_URL="https://centos.logs.rdoproject.org/"
        export LOG_PATH="${JOB_NAME}/${BUILD_NUMBER}/logs"
        export SUCCESS=${SUCCESS}
        bash -ex ${CICO_USER_DIR}/${RDO_CONFIG_DIR}/ci-scripts/tripleo-upstream/dlrnapi_report.sh
EOF

# Run the playbook.
ansible-playbook -i "${ANSIBLE_HOSTS}" delorean-report.yaml

popd
