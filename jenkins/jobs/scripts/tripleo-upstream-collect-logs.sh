set -ex
ANSIBLE_HOSTS=${ANSIBLE_HOSTS:-$WORKSPACE/hosts}
LOGSERVER="logs.rdoproject.org ansible_user=uploader"

# Add logserver to the ansible_hosts file
cat << EOF >> ${ANSIBLE_HOSTS}
[logserver]
${LOGSERVER}
EOF

# Create folder to place kolla logs in
sudo mkdir -p /var/log/kolla/logs/

# Create a playbook to pull the logs down from our cico node
cat << EOF > collect-logs.yml
- name: Collect logs from cico node
  hosts: openstack_nodes
  tasks:
      synchronize:
          mode: pull
          src: /tmp/kolla/logs/"
          dest: "/var/log/kolla/logs/"
          rsync_path: "sudo rsync"
EOF

# Run playbook
ansible-playbook -i "${ANSIBLE_HOSTS}" collect-logs.yml

# Prep logs for upload
cat << EOF > prep-logs.yml
- name: Prepare logs for upload
  hosts: logserver
  gather_facts: false
  tasks:
    - block:
        - name: Create log destination directory
          file:
            path: "/var/www/html/ci.centos.org/${JOB_NAME}/${BUILD_NUMBER}"
            state: "directory"
            recurse: "yes"
EOF

# Run playbook
ansible-playbook -i "${ANSIBLE_HOSTS}" prep-logs.yml

# Create a playbook to pull the logs from the jenkins node, from the log server
cat << EOF > upload-logs.yml
- name: Pull logs to upload sever
  hosts: logserver
  tasks:
      - block:
          - name: Pull build logs from VM to logserver
            vars:
                ssh_opts: "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"
                src: "/var/log/kolla/logs"
                host: "{{ ansible_user }}@{{ ansible_default_ipv4.address }}
                path "/var/www/html/ci.centos.org/${JOB_NAME}/${BUILD_NUMBER}"
            shell:
                sudo rsync -e "{{ ssh_opts }}" -avzR {{ host }}:{{ src }} {{ path }}
EOF

# Run playbook
ansible-playbook -i "${ANSIBLE_HOSTS}" upload-logs.yml
