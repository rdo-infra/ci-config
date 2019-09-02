virtualenv $WORKSPACE/venv_dlrnapi
source $WORKSPACE/venv_dlrnapi/bin/activate

pip install dlrnapi_client shyaml

curl -sLo $BUILD_TAG.yaml $(echo $DELOREAN_URL | sed 's/delorean\.repo/commit.yaml/')

commit_hash=$(cat $BUILD_TAG.yaml| shyaml get-value commits.0.commit_hash)
distro_hash=$(cat $BUILD_TAG.yaml| shyaml get-value commits.0.distro_hash)

dlrnapi --url https://$DELOREAN_PUBLIC_HOST/api-$RDO_VERSION \
    --username ciuser \
    report-result \
    --job-id $JOB_NAME \
    --commit-hash $commit_hash \
    --distro-hash $distro_hash \
    --timestamp $(date +%s) \
    --info-url https://ci.centos.org/job/$JOB_NAME/$BUILD_ID/artifact/console.txt.gz \
    --success $JOB_SUCCESS
