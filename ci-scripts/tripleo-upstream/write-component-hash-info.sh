set -ex
mkdir -p $WORKSPACE/logs
exec &> >(tee -i -a $WORKSPACE/logs/get_components_hash_log.log )

echo ======== PREPARE COMPINENT HASH INFO

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $SCRIPT_DIR/dlrnapi_venv.sh

trap deactivate_dlrnapi_venv EXIT
activate_dlrnapi_venv

set -u

: ${MD5_REPO:="$WORKSPACE/delorean.repo"}

COMP_REPO_URL_LIST=$(cat $MD5_REPO  | grep  'baseurl=' | cut -d '=' -f 2)
echo $COMP_REPO_URL_LIST

for REPO_URL in $COMP_REPO_URL_LIST; do
    curl -sLo commit.yaml $REPO_URL/commit.yaml
    COMPONENT_NAME=$(shyaml get-value commits.0.component < $WORKSPACE/commit.yaml)
    COMMIT_HASH=$(shyaml get-value commits.0.commit_hash < $WORKSPACE/commit.yaml)
    DISTRO_HASH=$(shyaml get-value commits.0.distro_hash < $WORKSPACE/commit.yaml)
    FULL_HASH=${COMMIT_HASH}_${DISTRO_HASH:0:8}

    cat > $WORKSPACE/${COMPONENT_NAME}_hash_info.sh << EOF
    export FULL_HASH=$FULL_HASH
    export COMMIT_HASH=$COMMIT_HASH
    export DISTRO_HASH=$DISTRO_HASH
    export COMPONENT_NAME=$COMPONENT_NAME
EOF
done

cp $WORKSPACE/${COMPONENT_NAME}_hash_info.sh $WORKSPACE/logs

echo ======== PREPARE COMPONENT HASH INFO COMPLETE
