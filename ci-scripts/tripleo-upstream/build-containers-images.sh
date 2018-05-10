set -e

echo ======== BUILD CONTAINERS IMAGES

# Retrieve role
mkdir -p $WORKSPACE/roles
pushd $WORKSPACE/roles
    git clone https://github.com/rdo-infra/ansible-role-rdo-kolla-build rdo-kolla-build
popd

# Delete any leftover configuration ansible
rm -f $WORKSPACE/ansible.cfg
TESTING_TAG="tripleo-ci-testing"
# devstack gate sets this, but conflicts with anything else
unset ANSIBLE_STDOUT_CALLBACK
export ANSIBLE_HOST_KEY_CHECKING=False
export ANSIBLE_ROLES_PATH="$WORKSPACE/roles"

# remove the last line of the file, the endblock statement
sed '$d' /usr/share/openstack-tripleo-common-containers/container-images/tripleo_kolla_template_overrides.j2
cat <<EOF >>/usr/share/openstack-tripleo-common-containers/container-images/tripleo_kolla_template_overrides.j2
# In order to ensure that we have the last base packages, we would like to do
# a yum update in the kolla base image. All the other images should inherit this
# but if the base distro container is out of date (i.g. 7.4 but 7.5 is out) this
# will pull in the updated packages available. Related issue LP#1770355
RUN yum update -y
{% endblock %}
EOF

cat << EOF > $WORKSPACE/playbook.yml
---
- name: Build Kolla images
  hosts: localhost
  become: yes
  become_user: root
  vars:
    kolla_namespace: "tripleo${RELEASE}"
    kolla_push: true
    kolla_tag: "$TESTING_TAG"
    openstack_release: "$RELEASE"
    trunk_repository: "https://trunk.rdoproject.org/centos7-$RELEASE/$TESTING_TAG/delorean.repo"
  tasks:
    - include_role:
        name: "rdo-kolla-build"
EOF

ansible-playbook $WORKSPACE/playbook.yml -e kolla_threads=16

echo ======== BUILD CONTAINERS IMAGES COMPLETED
