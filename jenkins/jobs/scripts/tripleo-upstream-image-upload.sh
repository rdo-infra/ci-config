set -ex
CICO_USER_DIR=${CICO_USER_DIR:-/root}
WORKSPACE=${WORKSPACE:-/tmp}
ANSIBLE_HOSTS=${ANSIBLE_HOSTS:-$WORKSPACE/hosts}
CONTAINER_BUILD_LOG_DIR=${CONTAINER_LOG_DIR:-container-builds}
LOGSERVER="logserver.rdoproject.org ansible_user=loguser"
LOG_DISPLAY_URL="https://logserver.rdoproject.org/ci.centos.org/${JOB_NAME}/${BUILD_NUMBER}"
CI_CENTOS_URL="https://ci.centos.org/job/${JOB_NAME}/${BUILD_NUMBER}"
SOURCE="${CICO_USER_DIR}/workspace/"
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

cat << EOF > upload-images.yaml
# Create a playbook to pull the images down from our cico node
- name: Collect images from cico node
  hosts: openstack_nodes
  gather_facts: no
  tasks:
    - name: 'Collect overcloud-full image from cico node'
      synchronize:
          mode: pull
          src: "${CICO_USER_DIR}/overcloud-full.tar"
          dest: "${WORKSPACE}"
EOF

# We keep connecting onto the same hosts that are continuously reinstalled
export ANSIBLE_HOST_KEY_CHECKING=False

# Run the playbook to grab images
ansible-playbook --ssh-extra-args="-o UserKnownHostsFile=/dev/null" -vvv -i "${ANSIBLE_HOSTS}" collect-images.yaml

# Upload images
DISTRO="centos8-ppc64le"
RELEASE="master"
UPLOAD_URL=uploader@images.rdoproject.org:/var/www/html/images/$DISTRO/$RELEASE/rdo_trunk
./review.rdoproject.org-config/ci-scripts/tripleo-upstream/upload-cloud-images.sh

popd
