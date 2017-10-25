#!/bin/bash
# Script to promote qcow images on rdoproject (images.rdoproject.org)
# Usage: promote-images.sh <release> <promoted_hash> <link_name>
# Example: promote-images.sh master f442a3aa35981c3d6d7e312599dde2a1b1d202c9_0468cca4 current-tripleo

set -eux

RELEASE=$1
PROMOTED_HASH=$2
LINK_NAME=$3

function sftp_command {
    echo "$1" | sftp \
        -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        uploader@images.rdoproject.org
}

sftp_command "rm /var/www/html/images/$RELEASE/rdo_trunk/$LINK_NAME"
sftp_command "ln -s /var/www/html/images/$RELEASE/rdo_trunk/$PROMOTED_HASH /var/www/html/images/$RELEASE/rdo_trunk/$LINK_NAME"
