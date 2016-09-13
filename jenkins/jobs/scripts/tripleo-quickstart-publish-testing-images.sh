set -eux

export VIRTHOST=$(head -n1 $WORKSPACE/virthost)

# this script is injected via raw-escape (in JJB).  It assumes a few variables are set.
echo $VIRTHOST
echo $RDO_VERSION_DIR
echo $BUILD_SYS
echo $LOCATION

# relative path used to publish images
dest_image_path="$RDO_VERSION_DIR/$BUILD_SYS/$LOCATION/testing/"

# ci.centos *MUST* use rsync (note "::", see rsync man page)
dest_centos_artifacts="rdo@artifacts.ci.centos.org::rdo/images/$dest_image_path"

# RDO file server can use scp
dest_rdo_filer="images.rdoproject.org:/var/www/html/images/$dest_image_path"

# where the files are parked on the virthost post-build
virthost_source_location="/var/lib/oooq-images"

# what to archive.
artifact_list="\
undercloud.qcow2 \
undercloud.qcow2.md5 \
ironic-python-agent.tar \
ironic-python-agent.tar.md5 \
overcloud-full.tar \
overcloud-full.tar.md5 \
artib-logs.tar.gz \
artib-logs.tar.gz.md5"

echo $artifact_list

# push --> artifacts server (rsync)
ssh root@$VIRTHOST "cd $virthost_source_location && rsync -av $artifact_list $dest_centos_artifacts"

# push --> RDO file server (scp)
scp_opts="-v -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
ssh root@$VIRTHOST "cd $virthost_source_location && scp $scp_opts $artifact_list $dest_rdo_filer"

