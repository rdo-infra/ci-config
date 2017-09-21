#!/bin/bash
# Script to promote qcow images on rdoproject (images.rdoproject.org)
# Usage: promote-images.sh <release> <promoted_hash> <link_name>
# Example: promote-images.sh master f442a3aa35981c3d6d7e312599dde2a1b1d202c9_0468cca4 current-tripleo

set -eux

RELEASE=$1
PROMOTED_HASH=$2
LINK_NAME=$3

image_path="$RELEASE/rdo_trunk/$LINK_NAME"
ssh_cmd='ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'

# Create local symlink
mkdir $PROMOTED_HASH
ln -s $PROMOTED_HASH stable

# Delete old stable symlink and old images
mkdir $LINK_NAME
rsync -av --delete --exclude $PROMOTED_HASH $LINK_NAME/ uploader@images.rdoproject.org:/var/www/html/images/$image_path/

# push symlink to RDO file server
rsync -av stable uploader@images.rdoproject.org:/var/www/html/images/$image_path/stable
