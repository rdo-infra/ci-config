set -eu

echo ======== PREPARE HASH INFO

# The script assumes that RELEASE and PROMOTE_NAME is set

virtualenv --system-site-packages $WORKSPACE/dlrnapi_venv
source $WORKSPACE/dlrnapi_venv/bin/activate
pip install dlrnapi_client shyaml

curl -sLo $WORKSPACE/commit.yaml https://trunk.rdoproject.org/centos7-$RELEASE/$PROMOTE_NAME/commit.yaml

COMMIT_HASH=$(shyaml get-value commits.0.commit_hash < $WORKSPACE/commit.yaml)
DISTRO_HASH=$(shyaml get-value commits.0.distro_hash < $WORKSPACE/commit.yaml)
FULL_HASH=${COMMIT_HASH}_${DISTRO_HASH:0:8}

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

mkdir $WORKSPACE/logs
cp $WORKSPACE/hash_info.sh $WORKSPACE/logs

deactivate
echo ======== PREPARE HASH INFO COMPLETE
