export ANSIBLE_ROLES_PATH=$PWD/roles

source OS credentials
unset OS_TENANT__{name, ID}
create ansible virtualenv
install ansible shade
add virtualenv python path to inventory
ansible-playbook -vvvv -i inventory.ini playbooks/main.yaml -e "ansible_python_interpreter='$VIRTUAL_ENV/bin/python'"
