export NEW_HASH=`curl $DELOREAN_URL | grep baseurl | awk -F '/' '{ print $5"/"$6"/"$7 }'`
export OLD_HASH=`curl $LAST_PROMOTED_URL | grep baseurl | awk -F '/' '{ print $5"/"$6"/"$7 }'`

echo "delorean_current_hash = $NEW_HASH" > $HASH_FILE

# These variables are used for the tripleo-quickstart-publish-testing-images
# script to put images in the correct location.
echo "LOCATION = $LOCATION" >> $HASH_FILE
echo "BUILD_SYS = $BUILD_SYS" >> $HASH_FILE
echo "RDO_VERSION_DIR = $RDO_VERSION_DIR" >> $HASH_FILE
echo "tempest_version = $TEMPEST_VERSION" >> $HASH_FILE
