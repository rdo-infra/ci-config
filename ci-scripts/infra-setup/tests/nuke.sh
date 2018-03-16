#!/bin/bash

ansible-playbook -vv -i ../inventories/inventory.ini -e @nuke.yml ../teardown.yml
