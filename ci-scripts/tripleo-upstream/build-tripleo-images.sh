set -e

echo ======== BUILD TRIPLEO IMAGES

# Retrieve role
mkdir -p $WORKSPACE/roles
pushd $WORKSPACE/roles
    git clone https://github.com/redhat-openstack/ansible-role-tripleo-image-build tripleo-image-build
popd

# Delete any leftover configuration ansible
rm -f $WORKSPACE/ansible.cfg
TESTING_TAG="tripleo-ci-testing"
# devstack gate sets this, but conflicts with anything else
unset ANSIBLE_STDOUT_CALLBACK
export ANSIBLE_HOST_KEY_CHECKING=False
export ANSIBLE_ROLES_PATH="$WORKSPACE/roles"

cat << EOF > $WORKSPACE/playbook.yml
---
- name: Build Triple O images
  hosts: localhost
  become: yes
  become_user: root
  vars:
    openstack_release: "$RELEASE"
  tasks:
    - include_role:
        name: "tripleo-image-build"
EOF

ansible-playbook $WORKSPACE/playbook.yml -e kolla_threads=16

echo ======== BUILD TRIPLEO IMAGES COMPLETED
