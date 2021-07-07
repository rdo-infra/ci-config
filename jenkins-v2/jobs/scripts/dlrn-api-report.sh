virtualenv $WORKSPACE/venv_dlrnapi
source $WORKSPACE/venv_dlrnapi/bin/activate

pip install dlrnapi_client shyaml

if [[ "$delorean_current_hash" == *"_"* ]]; then
    curl -sLo $BUILD_TAG.yaml $(echo $DELOREAN_URL | sed 's/delorean\.repo/commit.yaml/')
    COMMIT_HASH=$(cat $BUILD_TAG.yaml| shyaml get-value commits.0.commit_hash)
    DISTRO_HASH=$(cat $BUILD_TAG.yaml| shyaml get-value commits.0.distro_hash)
    HASH_ARGS="--commit-hash $COMMIT_HASH --distro-hash $DISTRO_HASH"
else
    AGG_HASH=`curl -L ${DELOREAN_URL}.md5`
    HASH_ARGS="--agg-hash $AGG_HASH"
fi

dlrnapi --url https://$DELOREAN_PUBLIC_HOST/api-$RDO_VERSION \
    --username ciuser \
    report-result \
    --job-id $JOB_NAME \
    ${HASH_ARGS} \
    --timestamp $(date +%s) \
    --info-url https://jenkins-cloudsig-ci.apps.ocp.ci.centos.org/job/$JOB_NAME/$BUILD_ID/console.txt.gz \
    --success $JOB_SUCCESS
