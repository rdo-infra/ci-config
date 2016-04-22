#!/bin/bash
# A script that releases nodes from a SSID file written by
# cico-node-get-to-ansible.sh
SSID_FILE=${SSID_FILE:-$WORKSPACE/cico-ssid}

for ssid in $(cat ${SSID_FILE})
do
    cico -q node done $ssid
done
