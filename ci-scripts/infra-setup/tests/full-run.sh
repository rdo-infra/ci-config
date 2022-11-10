#!/bin/bash

ansible-playbook -vvvv -i ../inventory/ ../full-run.yml -e cloud="vexxhost" -e bastion_private_key="$1" -e default_flavor=m1.medium
