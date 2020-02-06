#!/bin/bash
set -euo pipefail

# defaults used for backwards compatibility
: ${OPT_DISTRO:=centos}
: ${OPT_DISTRO_VERSION:=7}
: ${OPT_WEBROOT:=/var/www/html/images}
: ${OPT_WEBSITE:=https://images.rdoproject.org}
: ${IMAGE_SERVER_USER_HOST:=uploader@images.rdoproject.org}

function usage {
    cat <<-EOF
    Script to promote qcow images on ${OPT_WEBSITE}
    Usage: promote-images.sh [--distro centos] [--distro-version 7] <release> <promoted_hash> <link_name>
    Example: promote-images.sh master f442a3aa35981c3d6d7e312599dde2a1b1d202c9_0468cca4 current-tripleo
EOF
}

function finish {
    rc=$?
    if [[ $rc -eq 0 ]]; then
        echo "INFO: $0 succeded updating ${TARGET_URL:-} to point to ${SOURCE_URL:-} " >&2
    else
        echo "ERROR: $0 failed with $rc exit code" >&2
    fi
    exit $rc
}
trap finish EXIT

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

DISTRO_AND_VERSION="${OPT_DISTRO}${OPT_DISTRO_VERSION}"
if [[ "${OPT_DISTRO}" == "rhel" ]]; then
    OPT_DISTRO="redhat"
    OPT_WEBSITE="http://38.145.34.141/rcm-guest/images"
    IMAGE_SERVER_USER_HOST=centos@38.145.34.141
    OPT_WEBROOT="/var/www/rcm-guest/images"
fi

function sftp_command {
    # "-b -" assures that sftp command exit code is returned
    sftp -b - \
        -o LogLevel=error -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        ${IMAGE_SERVER_USER_HOST} 1>&2 <<EOF
$1
EOF
}

# Check if this is promotion staging environment and override vars
# See if the file /tmp/stage-info.yaml exists and source vars from there
if [[ -f /tmp/stage-info.yaml ]]; then
    images_path=$(shyaml get-value overcloud_images.root < /tmp/stage-info.yaml)
    USER=$(shyaml get-value main.promoter_user < /tmp/stage-info.yaml)
    OPT_WEBSITE="file://$images_path"
    IMAGE_SERVER_USER_HOST="$USER@127.0.0.1"
    OPT_WEBROOT="$images_path"
fi

# check if target url exists and fail-fast if it doesn't
SOURCE_URL=${OPT_WEBSITE}/$DISTRO_AND_VERSION/$RELEASE/rdo_trunk/$PROMOTED_HASH
curl -L --silent --head --fail $SOURCE_URL >/dev/null || {
    echo "ERROR: The promoted hash was not found: $SOURCE_URL" >&2
    exit 3
}
# needed for new releases, keep it:
# very important for new releases, where some folders may not even exist
# "mkdir: Invalid flag -p" may be returned in some cases, do not use it.
# "-" prefix tells it to ignore errors (if folder already exists)
sftp_command "-mkdir ${OPT_WEBROOT}/$DISTRO_AND_VERSION/"
sftp_command "-mkdir ${OPT_WEBROOT}/$DISTRO_AND_VERSION/$RELEASE/"
sftp_command "-mkdir ${OPT_WEBROOT}/$DISTRO_AND_VERSION/$RELEASE/rdo_trunk/"

# sftp rename oldpath newpath
# remove n-1 image soft link
sftp_command "-rm ${OPT_WEBROOT}/$DISTRO_AND_VERSION/$RELEASE/rdo_trunk/previous-${LINK_NAME}"
# rename the current link to previous-$LINK_NAME to keep n-1 copy of image
sftp_command "-rename ${OPT_WEBROOT}/$DISTRO_AND_VERSION/$RELEASE/rdo_trunk/$LINK_NAME ${OPT_WEBROOT}/$DISTRO_AND_VERSION/$RELEASE/rdo_trunk/previous-${LINK_NAME}"
# promote new hash with link
sftp_command "ln -s ${OPT_WEBROOT}/$DISTRO_AND_VERSION/$RELEASE/rdo_trunk/$PROMOTED_HASH ${OPT_WEBROOT}/$DISTRO_AND_VERSION/$RELEASE/rdo_trunk/$LINK_NAME"

TARGET_URL=${OPT_WEBSITE}/$DISTRO_AND_VERSION/$RELEASE/rdo_trunk/$LINK_NAME
curl -L --silent --head --fail $TARGET_URL >/dev/null || {
    echo "ERROR: The target is invalid: $TARGET_URL" >&2
    exit 3
}
