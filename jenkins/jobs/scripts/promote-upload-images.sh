image_path="$RDO_VERSION_DIR/$BUILD_SYS/$LOCATION"
scp_cmd='scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'

mkdir -p stable

# get testing images from the ci.centos artifacts server
rsync -av rdo@artifacts.ci.centos.org::rdo/images/$image_path/testing/ stable/

# push images to ci.centos artifacts server
rsync -av stable/ rdo@artifacts.ci.centos.org::rdo/images/$image_path/stable/

# push images to RDO file server
$scp_cmd stable/* images.rdoproject.org:/var/www/html/images/$image_path/stable/

# remove images from jenkins slave
rm -rf stable