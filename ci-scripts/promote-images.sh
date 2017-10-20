#!/bin/bash
# Script to promote qcow images on rdoproject (images.rdoproject.org)
# Usage: promote-images.sh -r <release> -p <promoted_hash> -l <link_name>
# Example: promote-images.sh -r master -p f442a3aa35981c3d6d7e312599dde2a1b1d202c9_0468cca4 -l current-tripleo

set -eux

DRY_RUN=0

while [ "x$1" != "x" ] ; do
    case "$1" in
        --release|-r)
            RELEASE=$1
            shift 2
            ;;
        --promoted-hash|-p)
            PROMOTED_HASH=$1
            shift 2
            ;;
        --link-name|-l)
            LINK_NAME=$1
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
    esac 
done

function sftp_command {
    echo "$1" | sftp \
        -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        uploader@images.rdoproject.org
}

if [[ "$DRY_RUN" != 1 && -n "$RELEASE" && -n "$PROMOTED_HASH" && -n "$LINK_NAME" ]]; then
    sftp_command "rm /var/www/html/images/$RELEASE/rdo_trunk/$LINK_NAME"
    sftp_command "ln -s $PROMOTED_HASH /var/www/html/images/$RELEASE/rdo_trunk/$LINK_NAME"
else
    sftp_command "ls /var/www/html/images/$RELEASE/rdo_trunk/$LINK_NAME"
    echo "ln -s $PROMOTED_HASH /var/www/html/images/$RELEASE/rdo_trunk/$LINK_NAME"
fi
