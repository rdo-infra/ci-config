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

# images.rdoproject will use rsync as well, but via ssh 
dest_rdo_filer="images.rdoproject.org:/var/www/html/images/$dest_image_path"

ssh_args="-v -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

# $RSYNC_PASSWORD is set as part of JJB / jenkins config, and is needed for artifacts server, but not for images.rdoproject.org
rsync_base_cmd="rsync --verbose --archive --delay-updates"
rsync_artifacts_cmd="RSYNC_PASSWORD=$RSYNC_PASSWORD $rsync_base_cmd"

# where the files are parked on the virthost post-build
virthost_source_location="/var/lib/oooq-images"

# what to archive
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

# rsync isn't on duffy nodes by default
ssh $ssh_args root@$VIRTHOST "yum install -y rsync"

# push --> artifacts server (rsync)
ssh $ssh_args root@$VIRTHOST "cd $virthost_source_location && $rsync_artifacts_cmd $artifact_list $dest_centos_artifacts"

# TODO: we've talked about using ssh agent fwd'ing here, but it involves a number of config steps
# TODO: on multiple hosts/nodes.  For now just doing the slightly less awesome "copy key and use it"

# copy the key
scp $ssh_args ~/.ssh/rdo-ci-public.pem root@$VIRTHOST:$virthost_source_location

# use key to rsync to images.rdoproject.org
ssh $ssh_args root@$VIRTHOST "cd $virthost_source_location && $rsync_base_cmd -e 'ssh -i rdo-ci-public.pem' $artifact_list $dest_rdo_filer"

