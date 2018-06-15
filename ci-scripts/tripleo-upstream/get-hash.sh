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

    # FIXME: Delete this
    # From https://review.rdoproject.org/jenkins/job/periodic-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset035-master/359/consoleFull
    export COMMIT_HASH=9f3a41c2c752bd68a84b6bd72add18e8bc6f4c76
    export DISTRO_HASH=f1a4ee5af8530044a9714efcbf99466535e1f9bf
    export FULL_HASH=9f3a41c2c752bd68a84b6bd72add18e8bc6f4c76_f1a4ee5a
elif [ "$RELEASE" = "queens" -a "$PROMOTE_NAME" = "consistent" ]; then

    # FIXME: Delete this
i   # From https://review.rdoproject.org/jenkins/job/periodic-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset001-queens/298/consoleText
    export COMMIT_HASH=bc3b37067c2008b55059a29045b579be43af9c65
    export DISTRO_HASH=1462a2567ed87a42190dbb935ff9044626b3e4f9
    export FULL_HASH=bc3b37067c2008b55059a29045b579be43af9c65_1462a256
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
