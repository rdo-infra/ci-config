set -e

echo ======== REPORT STATUS

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $SCRIPT_DIR/dlrnapi_venv.sh

trap deactivate_dlrnapi_venv EXIT
activate_dlrnapi_venv

set -u

source $WORKSPACE/hash_info.sh

dlrnapi --url $DLRNAPI_URL \
    --username ciuser \
    report-result \
    --job-id $JOB_NAME \
    --commit-hash $COMMIT_HASH \
    --distro-hash $DISTRO_HASH \
    --timestamp $(date +%s) \
    --info-url https://ci.centos.org/artifacts/rdo/$BUILD_TAG/console.txt.gz \
    --success $JOB_SUCCESS

echo ======== REPORT STATUS COMPLETE
