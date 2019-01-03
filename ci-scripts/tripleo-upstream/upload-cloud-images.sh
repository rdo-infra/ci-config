set -e
echo ======== UPLOAD CLOUD IMAGES
export FULL_HASH=$(grep -o -E '[0-9a-f]{40}_[0-9a-f]{8}' < /etc/yum.repos.d/delorean.repo)

pushd $HOME

ls *.tar

export RSYNC_RSH="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
rsync_cmd="rsync --verbose --archive --delay-updates --relative"

if [ -n "$DISTRO_NAME" ]; then
    UPLOAD_URL=uploader@images.rdoproject.org:/var/www/html/images/$DISTRO_NAME/$RELEASE/rdo_trunk
else
    UPLOAD_URL=uploader@images.rdoproject.org:/var/www/html/images/$RELEASE/rdo_trunk
fi

# Check if directory $FULL_HASH exists, if not create it.
if [ ! -d $FULL_HASH ]; then
    mkdir $FULL_HASH
fi
mv overcloud-full.tar overcloud-full.tar.md5 $FULL_HASH
mv ironic-python-agent.tar ironic-python-agent.tar.md5 $FULL_HASH

$rsync_cmd $FULL_HASH $UPLOAD_URL
$rsync_cmd --delete --include 'tripleo-ci-testing**' --exclude '*' ./ $UPLOAD_URL/
# Creating link to tripleo-ci-testing with actual $FULL_HASH
ln -s $FULL_HASH tripleo-ci-testing

rsync -av tripleo-ci-testing $UPLOAD_URL

popd
echo ======== UPLOAD CLOUD IMAGES COMPLETE
