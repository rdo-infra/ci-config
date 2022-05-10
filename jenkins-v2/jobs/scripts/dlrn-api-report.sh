#!/usr/bin/bash
# shellcheck disable=SC2154
# SC2154: delorean_current_hash is referenced but not assigned.


python3 -m venv "$WORKSPACE/venv_dlrnapi"
source "$WORKSPACE/venv_dlrnapi/bin/activate"

pip install dlrnapi_client shyaml

if [[ "$delorean_current_hash" == *"_"* ]]; then
    curl -sLo "$BUILD_TAG.yaml" "{$DELOREAN_URL//delorean\.repo/commit.yaml}"
    COMMIT_HASH=$(shyaml get-value commits.0.commit_hash < "$BUILD_TAG".yaml)
    DISTRO_HASH=$(shyaml get-value commits.0.distro_hash < "$BUILD_TAG".yaml)
    HASH_ARGS="--commit-hash $COMMIT_HASH --distro-hash $DISTRO_HASH"
else
    AGG_HASH=$(curl -L "${DELOREAN_URL}".md5)
    HASH_ARGS="--agg-hash $AGG_HASH"
fi

dlrnapi --url "https://$DELOREAN_PUBLIC_HOST/api-$RDO_VERSION" \
    --username ciuser \
    report-result \
    --job-id "$JOB_NAME" \
    "${HASH_ARGS}" \
    --timestamp "$(date +%s)" \
    --info-url "https://jenkins-cloudsig-ci.apps.ocp.ci.centos.org/job/$JOB_NAME/$BUILD_ID/console.txt.gz" \
    --success "$JOB_SUCCESS"
