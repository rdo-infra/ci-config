#!/bin/bash

ansible-playbook -vv -i ../inventory/ -e cloud="vexxhost" -e @nuke.yml ../teardown.yml
