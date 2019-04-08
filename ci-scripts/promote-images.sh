#!/bin/bash
# Script to promote qcow images on rdoproject (images.rdoproject.org)
# Usage: promote-images.sh <release> <promoted_hash> <link_name>
# Example: promote-images.sh master f442a3aa35981c3d6d7e312599dde2a1b1d202c9_0468cca4 current-tripleo

set -eux
: ${OPT_WEBROOT:=/var/www/html/images}

RELEASE=$1
PROMOTED_HASH=$2
LINK_NAME=$3

function sftp_command {
    # "-b -" assures that sftp command exit code is returned
    # we filter out some noise caused by lack of idempotency in sftp
    grep -v "Couldn't create directory: Failure" 1>&2 <(sftp -b - \
        -o LogLevel=error -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        uploader@images.rdoproject.org 2>&1 <<EOF
$1
EOF
)
}

# very important for new releases, where some folders may not even exist
# "mkdir: Invalid flag -p" may be returned in some cases, do not use it.
# "-" prefix tells it to ignore errors (if folder already exists)
sftp_command "-mkdir ${OPT_WEBROOT}/$RELEASE/"
sftp_command "-mkdir ${OPT_WEBROOT}/$RELEASE/rdo_trunk/"

# sftp rename oldpath newpath
# remove n-1 image soft link
sftp_command "-rm ${OPT_WEBROOT}/$RELEASE/rdo_trunk/previous-${LINK_NAME}"
# rename the current link to previous-$LINK_NAME to keep n-1 copy of image
sftp_command "-rename ${OPT_WEBROOT}/$RELEASE/rdo_trunk/$LINK_NAME ${OPT_WEBROOT}/$RELEASE/rdo_trunk/previous-${LINK_NAME}"
# promote new hash with link
sftp_command "ln -s ${OPT_WEBROOT}/$RELEASE/rdo_trunk/$PROMOTED_HASH ${OPT_WEBROOT}/$RELEASE/rdo_trunk/$LINK_NAME"

echo "INFO: New images should be accessible at https://images.rdoproject.com/$RELEASE/rdo_trunk/$LINK_NAME"
