#!/bin/bash

ansible-playbook -vvvv -i ../inventory/ ../provision-all.yml -e cloud="vexxhost"
