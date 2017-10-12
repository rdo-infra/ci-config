set -e
echo ======== CONVERT OVERCLOUD IMAGE TO UNDERCLOUD IMAGE

pushd $HOME
ls *.tar
tar -xf overcloud-full.tar

cat << EOF > convert-overcloud-undercloud.yml
---
- name: Convert an overcloud image to an undercloud
  hosts: localhost
  become: yes
  become_user: root
  vars:
    ansible_python_interpreter: /usr/bin/python
    repo_inject_image_path: "overcloud-full.qcow2"
    repo_run_live: false
    working_dir: ./
    overcloud_as_undercloud: true
  tasks:
    - include_role:
        name: "repo-setup"
    - include_role:
        name: "convert-image"
EOF

export ANSIBLE_ROLES_PATH="$HOME/.quickstart/usr/local/share/tripleo-quickstart/roles/"
ANSIBLE_ROLES_PATH="$ANSIBLE_ROLES_PATH:$HOME/.quickstart/usr/local/share/ansible/roles/"

export REPO_CONFIG="$HOME/.quickstart/config/release/tripleo-ci/$RELEASE.yml"
. .quickstart/bin/activate
ansible-playbook convert-overcloud-undercloud.yml
deactivate

md5sum undercloud.qcow2 > undercloud.qcow2.md5

echo ======== CONVERT COMPLETE

echo ======== UPLOAD UNDERCLOUD IMAGE
export FULL_HASH=$(grep -o -E '[0-9a-f]{40}_[0-9a-f]{8}' < /etc/yum.repos.d/delorean.repo)


chmod 600 $SSH_KEY
export RSYNC_RSH="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i $SSH_KEY"
rsync_cmd="rsync --verbose --archive --delay-updates --relative"
UPLOAD_URL=uploader@images.rdoproject.org:/var/www/html/images/$RELEASE/rdo_trunk
mkdir $FULL_HASH
mv undercloud.qcow2 undercloud.qcow2.md5 $FULL_HASH

$rsync_cmd $FULL_HASH $UPLOAD_URL

popd
echo ======== UPLOAD UNDERCLOUD COMPLETE
