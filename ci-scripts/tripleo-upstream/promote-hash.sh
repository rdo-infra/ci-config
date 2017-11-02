set -e

echo ======== PROMOTE HASH

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $SCRIPT_DIR/dlrnapi_venv.sh

trap deactivate_dlrnapi_venv EXIT
activate_dlrnapi_venv

source $WORKSPACE/hash_info.sh

if [ "$RELEASE" = "master" ]; then
    COMMIT_HASH=3b718f3fecc866332ec0663fa77e758f8346ab93
    DISTRO_HASH=4204ba89997cae739e41526b575027e333a2277d
fi

set -u

# Assign label to the specific hash using the DLRN API
dlrnapi --url $DLRNAPI_URL \
    --username review_rdoproject_org \
    repo-promote \
    --commit-hash $COMMIT_HASH \
    --distro-hash $DISTRO_HASH \
    --promote-name $PROMOTE_NAME

echo ======== PROMOTE HASH COMPLETED
