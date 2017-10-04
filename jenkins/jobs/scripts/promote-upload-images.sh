image_path="$RDO_VERSION_DIR/$BUILD_SYS/$LOCATION"
ssh_cmd='ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
PROMOTE_HASH=`echo $delorean_current_hash | awk -F '/' '{ print $3}'`

# Create local symlink
mkdir $PROMOTE_HASH
ln -s $PROMOTE_HASH stable

# Delete old stable symlink and old images
mkdir $LOCATION
rsync -av --delete --exclude $PROMOTE_HASH $LOCATION/ rdo@artifacts.ci.centos.org::rdo/images/$image_path/
# TDOD(gcerami): implement retention of previous promoted images
#rsync -av --delete --exclude $PROMOTE_HASH $LOCATION/ uploader@images.rdoproject.org:/var/www/html/images/$image_path/

# push symlink to ci.centos artifacts server
rsync -av stable rdo@artifacts.ci.centos.org::rdo/images/$image_path/stable

# push symlink to RDO file server
rsync -av stable uploader@images.rdoproject.org:/var/www/html/images/$image_path/stable
