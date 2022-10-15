#!/bin/bash

ansible-playbook -vvvv -i ../inventories/inventory.ini ../1_provision_cloud.yml
