#!/bin/bash

# Install ansible on local machine

sudo dnf install epel-release -y

sudo dnf install ansible -y


# Create separate hosts file to run the server_setup.yaml playbook
HOME_DIR = eval echo "~$USER"
cat <<EOF > $HOME_DIR/hosts
[localhost]
127.0.0.1 ansible_user=$USER
[promoter]
127.0.0.1 ansible_user=$USER
EOF

cat <<EOF
######################################################
Make sure ssh works fine for ansible and required host
######################################################

Make sure the ssh works fine for ansible and required
host for that check the below points:

    1. Check the ssh key present or not, If it's not
       present create the ssh key using the below
       command:
           ssh-keygen
    2. Check if authorized_keys file is present under
        /home/<user>/.ssh/ folder, if not then create it.
    3. Copy the public key </home/<user>/.ssh/id_rsa.pub>
       into /home/<user>/.ssh/authorized_keys file
    4. Set the below mode to /home/<user>/.ssh/authorized_keys file
         chmod 0600 /home/<user>/.ssh/authorized_keys
    5. Make ssh <user>@127.0.0.1 works fine with out password

EOF
