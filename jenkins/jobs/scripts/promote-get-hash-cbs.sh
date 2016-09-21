# This script is needed for the cases where we are testing CBS repos rather
# than trunk repos.

# (trown) We have a hardcoded assumption in the image promotion logic that we
# are using dlrn repos. In order to work around that so that we can get CBS
# promotion pipelines up, we give a fake delorean hash using seconds since
# epoch.
# We could likely redesign the image promotion in a better way.
echo "delorean_current_hash = 00/00/$(date +%s)" > $HASH_FILE

# These variables are used for the tripleo-quickstart-publish-testing-images
# script to put images in the correct location.
echo "LOCATION = $LOCATION" >> $HASH_FILE
echo "BUILD_SYS = $BUILD_SYS" >> $HASH_FILE
echo "RDO_VERSION_DIR = $RDO_VERSION_DIR" >> $HASH_FILE
