# TODO(arxcruz): This file is marked to be deleted
image_path="$RDO_VERSION_DIR/$BUILD_SYS/$LOCATION"
ssh_cmd='ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
PROMOTE_HASH=`echo $delorean_current_hash | awk -F '/' '{ print $3}'`
IMAGE_SERVER=${IMAGE_SERVER:-'images.rdoproject.org'}

# Create local symlink
mkdir $PROMOTE_HASH
ln -s $PROMOTE_HASH stable

# Delete old stable symlink and old images
mkdir $LOCATION
rsync -av --delete --exclude $PROMOTE_HASH $LOCATION/ rdo@artifacts.ci.centos.org::rdo/images/$image_path/
rsync -av --delete --exclude $PROMOTE_HASH $LOCATION/ uploader@$IMAGE_SERVER:/var/www/html/images/$image_path/

# push symlink to ci.centos artifacts server
rsync -av stable rdo@artifacts.ci.centos.org::rdo/images/$image_path/stable

# push symlink to RDO file server
rsync -av stable uploader@$IMAGE_SERVER:/var/www/html/images/$image_path/stable
