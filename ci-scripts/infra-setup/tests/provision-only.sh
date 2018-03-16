#!/bin/bash

ansible-playbook -vvvv -i ../inventories/inventory.ini ../provision-all.yml
