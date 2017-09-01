set -eu

echo ======== PROMOTE HASH

source $WORKSPACE/dlrnapi_venv/bin/activate
source $WORKSPACE/hash_info.sh

# Assign label to the specific hash using the DLRN API
dlrnapi --url $DLRNAPI_URL \
    --username review_rdoproject_org \
    repo-promote \
    --commit-hash $COMMIT_HASH \
    --distro-hash $DISTRO_HASH \
    --promote-name $PROMOTE_NAME

deactivate
echo ======== PROMOTE HASH COMPLETED
