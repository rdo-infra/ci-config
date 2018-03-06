source OS credentials
unset OS_TENANT__{name, ID}
create ansible virtualenv
install ansible shade
add virtualenv python path to inventory
ansible-playbook -i inventory.ini playbooks/main.yml -e 'ansible_python__intenpreter="$VIRTUAL_ENV/bin/python'
