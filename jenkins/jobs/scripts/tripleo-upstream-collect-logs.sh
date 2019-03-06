set -ex
ANSIBLE_HOSTS=${ANSIBLE_HOSTS:-$WORKSPACE/hosts}
LOGSERVER_URL="logs.rdoproject.org"
LOGSERVER="${LOGSERVER_URL} ansible_user=uploader"

# Add logserver to the ansible_hosts file
cat << EOF >> ${ANSIBLE_HOSTS}
[logserver]
${LOGSERVER}
EOF

# Create folder to place kolla logs in
mkdir -p $WORKSPACE/logs/

# Create a playbook to pull the logs down from our cico node
cat << EOF > collect-logs.yml
- name: Collect logs from cico node
  hosts: openstack_nodes
  tasks:
      synchronize:
          mode: pull
          src: /tmp/kolla/logs/"
          dest: "$WORKSPACE/logs/"
EOF

# Run playbook
ansible-playbook -i "${ANSIBLE_HOSTS}" collect-logs.yml

# Create a playbook to make a folder on the logserver, then push logs to it
cat << EOF > prep-logs.yml
- name: Create folder on logserver
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

cat << EOF > upload-logs.yml
- name: Upload logs to logserver
  hosts: localhost
  tasks:
    - block:
        - name: Push logs from Jenkins node to logserver
          vars:
              src: "$WORKSPACE/logs"
              host: "{{ ansible_user }}@{{ ansible_default_ipv4.address }}
              path "/var/www/html/ci.centos.org/${JOB_NAME}/${BUILD_NUMBER}"
          shell:
              rsync -avz {{ src }} ${LOGSERVER_URL}:{{ path }}
EOF

# Run playbook
ansible-playbook -i "${ANSIBLE_HOSTS}" upload-logs.yml
