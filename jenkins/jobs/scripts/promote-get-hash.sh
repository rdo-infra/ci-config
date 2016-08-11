export NEW_HASH=`curl $DELOREAN_URL | grep baseurl | awk -F '/' '{ print $5"/"$6"/"$7 }'`
export OLD_HASH=`curl $LAST_PROMOTED_URL | grep baseurl | awk -F '/' '{ print $5"/"$6"/"$7 }'`

# No need to run the whole promote pipeline if there is nothing new to promote
if [ $OLD_HASH == $NEW_HASH ]; then
    exit 23
fi

echo "delorean_current_hash = $NEW_HASH" > $HASH_FILE

# This is needed to make the promote image building job runnable outside of CI in the
# same way as the other tripleo-quickstart jobs.
echo "PUBLISH = true" >> $HASH_FILE

# Set the $LOCATION where quickstart will expect the images while testing in the pipeline
echo "LOCATION = $LOCATION" >> $HASHFILE

