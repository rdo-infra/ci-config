#!/bin/bash
# Script to clear old images on rdoproject (images.rdoproject.org)
# Usage: clear_images.sh <release>
# Example: clear_images.sh master


set -eux

RELEASE=$1

function sftp_command {
    echo "$1" | sftp \
        -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        uploader@images.rdoproject.org
}

sftp_command "cd /var/www/html/images/$RELEASE/rdo_trunk && \
    find /var/www/html/images/$RELEASE/rdo_trunk/* -type d -mtime +14 | \
    grep -vF \"$(readlink -f current-tripleo current-passed-ci tripleo-ci-testing consistent current-tripleo-rdo previous-current-tripleo)\" | \
    xargs --no-run-if-empty -t rm -rf"
