set -ex
mkdir -p $WORKSPACE/logs
exec &> >(tee -i -a $WORKSPACE/logs/get_hash_log.log )

echo ======== PREPARE HASH INFO

# The script assumes that RELEASE and PROMOTE_NAME is set

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $SCRIPT_DIR/dlrnapi_venv.sh

trap deactivate_dlrnapi_venv EXIT
activate_dlrnapi_venv

set -u
: ${DLRNAPI_DISTRO:="CentOS"}
: ${DLRNAPI_DISTRO_VERSION:="8"}
: ${DLRNAPI_SERVER:="trunk.rdoproject.org"}
: ${HTTP_PROTOCOL:="https"}

DLRNAPI_URL="${HTTP_PROTOCOL}://${DLRNAPI_SERVER}/api-${DLRNAPI_DISTRO,,}-$RELEASE"
if [[ "$RELEASE" == "master"  && "$DLRNAPI_DISTRO" == "CentOS" ]]; then
    # for master we have two DLRN builders, use the "upper constraint" one that
    # places restrictions on the maximum version of all dependencies
    export DLRNAPI_URL="${DLRNAPI_URL}-uc"
fi

HASHES_URL=${HTTP_PROTOCOL}://${DLRNAPI_SERVER}/${DLRNAPI_DISTRO,,}${DLRNAPI_DISTRO_VERSION}-$RELEASE/$PROMOTE_NAME/delorean.repo.md5
curl -sLo $WORKSPACE/delorean.repo.md5 $HASHES_URL
MD5_HASH=$(cat $WORKSPACE/delorean.repo.md5)

cat > $WORKSPACE/hash_info.sh << EOF
export DLRNAPI_URL=$DLRNAPI_URL
export RELEASE=$RELEASE
export FULL_HASH=$MD5_HASH
EOF

cp $WORKSPACE/hash_info.sh $WORKSPACE/logs

echo ======== PREPARE HASH INFO COMPLETE
