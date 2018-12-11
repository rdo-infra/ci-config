source $WORKSPACE/hash_info.sh
if [[ "$SUCCESS" = "true" ]]; then
    echo "REPORTING SUCCESS TO DLRN API"
else
    echo "REPORTING FAILURE TO DLRN API"
fi
sudo pip install dlrnapi-client
dlrnapi --url $DLRNAPI_URL \
    --username review_rdoproject_org \
    report-result \
    --commit-hash $COMMIT_HASH \
    --distro-hash $DISTRO_HASH \
    --job-id $JOB_NAME \
    --info-url "https://logs.rdoproject.org/$LOG_PATH" \
    --timestamp $(date +%s) \
    --success $SUCCESS

