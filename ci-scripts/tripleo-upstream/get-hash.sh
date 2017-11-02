set -e

echo ======== PREPARE HASH INFO

# The script assumes that RELEASE and PROMOTE_NAME is set

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $SCRIPT_DIR/dlrnapi_venv.sh

trap deactivate_dlrnapi_venv EXIT
activate_dlrnapi_venv

set -u

curl -sLo $WORKSPACE/commit.yaml https://trunk.rdoproject.org/centos7-$RELEASE/$PROMOTE_NAME/commit.yaml

COMMIT_HASH=$(shyaml get-value commits.0.commit_hash < $WORKSPACE/commit.yaml)
DISTRO_HASH=$(shyaml get-value commits.0.distro_hash < $WORKSPACE/commit.yaml)
FULL_HASH=${COMMIT_HASH}_${DISTRO_HASH:0:8}

export DLRNAPI_URL="https://trunk.rdoproject.org/api-centos-$RELEASE"
if [ "$RELEASE" = "master" ]; then
    # for master we have two DLRN builders, use the "upper constraint" one that
    # places restrictions on the maximum version of all dependencies
    export DLRNAPI_URL="${DLRNAPI_URL}-uc"
    COMMIT_HASH=3b718f3fecc866332ec0663fa77e758f8346ab93
    DISTRO_HASH=4204ba89997cae739e41526b575027e333a2277d
    FULL_HASH=3b718f3fecc866332ec0663fa77e758f8346ab93_4204ba89
fi

cat > $WORKSPACE/hash_info.sh << EOF
export DLRNAPI_URL=$DLRNAPI_URL
export RELEASE=$RELEASE
export FULL_HASH=$FULL_HASH
export COMMIT_HASH=$COMMIT_HASH
export DISTRO_HASH=$DISTRO_HASH
EOF

mkdir -p $WORKSPACE/logs
cp $WORKSPACE/hash_info.sh $WORKSPACE/logs

echo ======== PREPARE HASH INFO COMPLETE
