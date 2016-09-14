image_path="$RDO_VERSION_DIR/$BUILD_SYS/$LOCATION"
ssh_cmd='ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
PROMOTE_HASH=`echo $delorean_current_hash | awk -F '/' '{ print $3}'`

# Create local symlink
mkdir $PROMOTE_HASH
ln -s $PROMOTE_HASH stable

# push symlink to ci.centos artifacts server
rsync -av stable rdo@artifacts.ci.centos.org::rdo/images/$image_path/stable

# delete old images from artifacts server
mkdir $LOCATION
rsync -av --delete --exclude stable --exclude $PROMOTE_HASH $LOCATION/ rdo@artifacts.ci.centos.org::rdo/images/$image_path/

# push images to RDO file server
$ssh_cmd images.rdoproject.org "cp -f /var/www/html/images/$image_path/testing/* /var/www/html/images/$image_path/stable/"

