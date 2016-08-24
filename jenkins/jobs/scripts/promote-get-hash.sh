export NEW_HASH=`curl $DELOREAN_URL | grep baseurl | awk -F '/' '{ print $5"/"$6"/"$7 }'`
export OLD_HASH=`curl $LAST_PROMOTED_URL | grep baseurl | awk -F '/' '{ print $5"/"$6"/"$7 }'`

# RDO Promotion
# No need to test for RDO promotion if there is nothing new to promote
#
# Delivery Chain Pipeline
# The current-tripleo pin only updates as tripleo-ci promotes
# Allow the RDO tripleo promote pipeline to retest current-tripleo when manually executed
if [[ $OLD_HASH == $NEW_HASH ]] && [[ $DELOREAN_PIN != 'current-tripleo' ]]; then
    exit 23
fi

echo "delorean_current_hash = $NEW_HASH" > $HASH_FILE

# This is needed to make the promote image building job runnable outside of CI in the
# same way as the other tripleo-quickstart jobs.
echo "PUBLISH = true" >> $HASH_FILE

# Set the $LOCATION where quickstart will expect the images while testing in the pipeline
# This is used by the ansible-role-tripleo-image build (atrib) role and oooq/ci-scripts/image.sh
echo "LOCATION = $LOCATION" >> $HASH_FILE
