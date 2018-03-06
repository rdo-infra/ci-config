ansible-playbook -vvvv -i ../inventory.ini ../playbooks/full-run.yml -e bastion_private_key=$1
