if [[ "${RDO_VERSION}" == *"centos8"* ]] || [[ "${RDO_VERSION}" == *"centos9"* ]]; then
    export NEW_HASH=`curl -L ${DELOREAN_URL}.md5`
    export OLD_HASH=`curl -L ${LAST_PROMOTED_URL}.md5`

    NEW_HASH=${NEW_HASH:0:2}/${NEW_HASH:2:2}/${NEW_HASH}
    OLD_HASH=${OLD_HASH:0:2}/${OLD_HASH:2:2}/${OLD_HASH}
else
    export NEW_HASH=`curl -L $DELOREAN_URL | grep baseurl | awk -F '/' '{ print $5"/"$6"/"$7 }'`
    export OLD_HASH=`curl -L $LAST_PROMOTED_URL | grep baseurl | awk -F '/' '{ print $5"/"$6"/"$7 }'`
fi

# No need to run the whole promote pipeline if there is nothing new to promote
if [ $OLD_HASH == $NEW_HASH ]; then
    exit 23
fi

echo "delorean_current_hash = $NEW_HASH" > $HASH_FILE

# These variables are used for the tripleo-quickstart-publish-testing-images
# script to put images in the correct location.
echo "LOCATION = $LOCATION" >> $HASH_FILE
echo "BUILD_SYS = $BUILD_SYS" >> $HASH_FILE
echo "RDO_VERSION_DIR = ${RDO_VERSION_DIR}" >> $HASH_FILE
echo "RDO_VERSION = ${RDO_VERSION}" >> $HASH_FILE
echo "CICO_OS_RELEASE = ${CICO_OS_RELEASE:-8-stream}" >> $HASH_FILE
echo "ANSIBLE_PYTHON_INTERPRETER = ${ANSIBLE_PYTHON_INTERPRETER:-/usr/bin/python}" >> $HASH_FILE
echo "tempest_version = $TEMPEST_VERSION" >> $HASH_FILE
echo "enable_puppet_modules_rpm = $ENABLE_PUPPET_MODULES_RPM" >> $HASH_FILE
