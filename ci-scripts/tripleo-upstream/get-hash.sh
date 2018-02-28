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


## REMOVE ME, EMERGENCY PINNING FOR QUEENS PROMOTION

if [ $RELEASE == "queens" ] && [ $PROMOTE_NAME == "consistent" ]; then
    COMMIT_HASH=6f5ea2266845fbc95354233e626b5f46ebbe5da8
    DISTRO_HASH=ca3f9388602f90d1d1b8252e74c8ea3286cb90a6
    FULL_HASH=6f5ea2266845fbc95354233e626b5f46ebbe5da8_ca3f9388
fi

export DLRNAPI_URL="https://trunk.rdoproject.org/api-centos-$RELEASE"
if [ "$RELEASE" = "master" ]; then
    # for master we have two DLRN builders, use the "upper constraint" one that
    # places restrictions on the maximum version of all dependencies
    export DLRNAPI_URL="${DLRNAPI_URL}-uc"
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
