export ANSIBLE_ROLES_PATH=$PWD/roles


ansible-galaxy install -r ansible-role-requirements.yml 
source OS credentials
create ansible virtualenv
install ansible shade
ansible-playbook -vvvv -i inventory.ini playbooks/main.yaml -e bastion_private_key=/path/to/private_key
