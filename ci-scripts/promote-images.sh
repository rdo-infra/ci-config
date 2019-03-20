#!/bin/bash
# Script to promote qcow images on rdoproject (images.rdoproject.org)
# Usage: promote-images.sh <release> <promoted_hash> <link_name>
# Example: promote-images.sh master f442a3aa35981c3d6d7e312599dde2a1b1d202c9_0468cca4 current-tripleo

set -eux

RELEASE=$1
PROMOTED_HASH=$2
LINK_NAME=$3

function sftp_command {
    # "-b -" assures that sftp command exit code is returned
    sftp -b - \
        -o LogLevel=error -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        uploader@images.rdoproject.org <<EOF
$1
EOF
}

# needed for new releases, keep it:
sftp_command "mkdir /var/www/html/images/$RELEASE"
sftp_command "mkdir /var/www/html/images/$RELEASE/rdo_trunk/"
# sftp rename oldpath newpath
# remove n-1 image soft link
sftp_command "rm /var/www/html/images/$RELEASE/rdo_trunk/previous-${LINK_NAME}"
# rename the current link to previous-$LINK_NAME to keep n-1 copy of image
sftp_command "rename /var/www/html/images/$RELEASE/rdo_trunk/$LINK_NAME /var/www/html/images/$RELEASE/rdo_trunk/previous-${LINK_NAME}"
# promote new hash with link
sftp_command "ln -s /var/www/html/images/$RELEASE/rdo_trunk/$PROMOTED_HASH /var/www/html/images/$RELEASE/rdo_trunk/$LINK_NAME"

echo "INFO: New images should be accessible at https://images.rdoproject.com/$RELEASE/rdo_trunk/$LINK_NAME"
