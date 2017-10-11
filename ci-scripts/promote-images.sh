#!/bin/bash
# Script to promote qcow images on rdoproject (images.rdoproject.org)
# Usage: promote-images.sh <release> <promoted_hash> <link_name>
# Example: promote-images.sh master f442a3aa35981c3d6d7e312599dde2a1b1d202c9_0468cca4 current-tripleo

set -eux

RELEASE=$1
PROMOTED_HASH=$2
LINK_NAME=$3

# note: without --no-derefence the link gets created inside the $LINK_NAME
# directory named as $PROMOTED_HASH instead of a link named $LINK_NAME pointing
# to $PROMOTED_HASH
# the --force is also necessary to overwrite an existing link
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    uploader@images.rdoproject.org
    ln --symbolic --no-dereference --force \
    $PROMOTED_HASH /var/www/html/images/$RELEASE/rdo_trunk/$LINK_NAME

# cleaning up old images should happen on server side
