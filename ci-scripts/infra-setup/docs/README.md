export ANSIBLE_ROLES_PATH=$PWD/roles
source OS credentials
create ansible virtualenv
install ansible shade
ansible-playbook -vvvv -i inventories/inventory.ini full_run.yml
