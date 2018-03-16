#!/bin/bash

ansible-playbook -vvvv -i ../inventories/inventory.ini ../full-run.yml -e bastion_private_key=$1
