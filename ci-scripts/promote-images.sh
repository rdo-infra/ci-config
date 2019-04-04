#!/bin/bash
set -euo pipefail

# defaults used for backwards compatibility
: ${OPT_DISTRO:=centos}
: ${OPT_DISTRO_VERSION:=7}
: ${OPT_WEBSITE:=https://images.rdoproject.org}
: ${OPT_WEBROOT:=/var/www/html/images}

function usage {
    cat <<EOF
Script to promote qcow images on ${OPT_WEBSITE}
Usage: promote-images.sh [--distro centos] [--distro-version 7] <release> <promoted_hash> <link_name>
Example: promote-images.sh master f442a3aa35981c3d6d7e312599dde2a1b1d202c9_0468cca4 current-tripleo
EOF
}

function finish {
    rc=$?
    if [[ $rc -eq 0 ]]; then
        echo "INFO: $0 succeded updating ${OPT_WEBSITE}/$BLEND/$RELEASE/rdo_trunk/$LINK_NAME" >&2
    else
        echo "ERROR: $0 failed with $rc exit code" >&2
    fi
    exit $rc
}
trap finish EXIT

# positional args
args=()
while [ "x${1:-}" != "x" ]; do
    case "$1" in
        --distro)
            # we lowercase distro string, to avoid accidents
            OPT_DISTRO=$(echo $2| tr '[:upper:]' '[:lower:]')
            shift
            ;;
        --distro-version)
            OPT_DISTRO_VERSION=$2
            shift
            ;;
        -*) echo "ERROR: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            break
            ;;
    esac
    shift
done

if [ "$#" -ne 3 ]; then
    usage >&2
    echo "ERROR: invalid number of parameters" >&2
    exit 2
fi

RELEASE=$1
PROMOTED_HASH=$2
LINK_NAME=$3

BLEND="${OPT_DISTRO}${OPT_DISTRO_VERSION}"

function sftp_command {
    echo "DEBUG: sftp: $1" >&2
    echo "$1" | sftp \
    -o LogLevel=error -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        uploader@images.rdoproject.org
}

# check if target url exists and fail-fast if it doesn't
curl -L --silent --head --fail ${OPT_WEBSITE}/$BLEND/$RELEASE/rdo_trunk/$PROMOTED_HASH >/dev/null || {
    echo "ERROR: The source is invalid: ${OPT_WEBSITE}/$BLEND/$RELEASE/rdo_trunk/$PROMOTED_HASH" >&2
    exit 3
}

# sftp rename oldpath newpath
# remove n-1 image soft link
sftp_command "rm ${OPT_WEBROOT}/$BLEND/$RELEASE/rdo_trunk/previous-${LINK_NAME}"
# rename the current link to previous-$LINK_NAME to keep n-1 copy of image
sftp_command "rename ${OPT_WEBROOT}/$BLEND/$RELEASE/rdo_trunk/$LINK_NAME ${OPT_WEBROOT}/$BLEND/$RELEASE/rdo_trunk/previous-${LINK_NAME}"
# promote new hash with link
sftp_command "ln -s ${OPT_WEBROOT}/$BLEND/$RELEASE/rdo_trunk/$PROMOTED_HASH ${OPT_WEBROOT}/$BLEND/$RELEASE/rdo_trunk/$LINK_NAME"

# validate that the new urls is still in place
curl -L --silent --head --fail ${OPT_WEBSITE}/$BLEND/$RELEASE/rdo_trunk/$LINK_NAME >/dev/null || {
    echo "ERROR: The target is invalid: ${OPT_WEBSITE}/$BLEND/$RELEASE/rdo_trunk/$LINK_NAME" >&2
    exit 3
}
