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
: ${DLRNAPI_DISTRO_VERSION:="7"}
: ${DLRNAPI_SERVER:="trunk.rdoproject.org"}
: ${HTTP_PROTOCOL:="https"}
: ${COMPONENT_NAME:=""}

DLRNAPI_URL="${HTTP_PROTOCOL}://${DLRNAPI_SERVER}/api-${DLRNAPI_DISTRO,,}-$RELEASE"
if [[ "$RELEASE" == "master"  && "$DLRNAPI_DISTRO" == "CentOS" ]]; then
    # for master we have two DLRN builders, use the "upper constraint" one that
    # places restrictions on the maximum version of all dependencies
    export DLRNAPI_URL="${DLRNAPI_URL}-uc"
fi

# NO release or version in fedora url e.g. https://trunk.rdoproject.org/centos7-master/consistent/commit.yaml
# vs https://trunk.rdoproject.org/fedora/consistent/commit.yaml
# for fedora master trunk.rdoproject.org/fedora
if [[ "$RELEASE" == "master"  && "${DLRNAPI_DISTRO,,}" == "fedora" ]]; then
    HASHES_URL=${HTTP_PROTOCOL}://${DLRNAPI_SERVER}/${DLRNAPI_DISTRO,,}/$PROMOTE_NAME/commit.yaml
# for fedora stein  trunk.rdoproject.org/fedora-stein
# will need an elif here
elif [[ "$COMPONENT_NAME" != '' ]]; then
    HASHES_URL=${HTTP_PROTOCOL}://${DLRNAPI_SERVER}/${DLRNAPI_DISTRO,,}${DLRNAPI_DISTRO_VERSION}-$RELEASE/component/$COMPONENT_NAME/$PROMOTE_NAME/commit.yaml
else
    HASHES_URL=${HTTP_PROTOCOL}://${DLRNAPI_SERVER}/${DLRNAPI_DISTRO,,}${DLRNAPI_DISTRO_VERSION}-$RELEASE/$PROMOTE_NAME/commit.yaml
fi

curl -sLo $WORKSPACE/commit.yaml $HASHES_URL

COMMIT_HASH=$(shyaml get-value commits.0.commit_hash < $WORKSPACE/commit.yaml)
DISTRO_HASH=$(shyaml get-value commits.0.distro_hash < $WORKSPACE/commit.yaml)
EXTENDED_HASH=$(shyaml get-value commits.0.extended_hash < $WORKSPACE/commit.yaml)
FULL_HASH=${COMMIT_HASH}_${DISTRO_HASH:0:8}

# Check if an extended_hash is defined and add to full_hash
# and hash_info.sh
if [ "$EXTENDED_HASH" != 'None' ]; then
    EXTENDED_HASH_FIRST=$(echo $EXTENDED_HASH | cut -d'_' -f1)
    EXTENDED_HASH_SECOND=$(echo $EXTENDED_HASH | cut -d'_' -f2)
    FULL_HASH=${COMMIT_HASH}_${DISTRO_HASH:0:8}_${EXTENDED_HASH_FIRST:0:8}_${EXTENDED_HASH_SECOND:0:8}
fi

cat > $WORKSPACE/hash_info.sh << EOF
export DLRNAPI_URL=$DLRNAPI_URL
export RELEASE=$RELEASE
export FULL_HASH=$FULL_HASH
export COMMIT_HASH=$COMMIT_HASH
export DISTRO_HASH=$DISTRO_HASH
export COMPONENT_NAME=$COMPONENT_NAME
EOF

if [ "$EXTENDED_HASH" != 'None' ]; then
cat >> $WORKSPACE/hash_info.sh << EOF
export EXTENDED_HASH=$EXTENDED_HASH
EOF
fi

cp $WORKSPACE/hash_info.sh $WORKSPACE/logs

echo ======== PREPARE HASH INFO COMPLETE
