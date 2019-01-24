set -eux

pushd $WORKSPACE

git clone https://github.com/rdo-infra/ci-config
git clone https://git.openstack.org/openstack/tripleo-quickstart

bash tripleo-quickstart/ci-scripts/get-node.sh

export VIRTHOST=$(head -n1 $WORKSPACE/virthost)
echo $VIRTHOST

ssh_args="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

# where to build on the virthost
virthost_source_location="/var/lib/oooq-images"

build_script="$WORKSPACE/ci-config/ci-scripts/build-images.sh"

# make directory to build on the virthost
ssh $ssh_args root@$VIRTHOST "mkdir -p $virthost_source_location"

# copy build script to virthost
scp $ssh_args $build_script root@$VIRTHOST:$virthost_source_location

# run the build script
ssh $ssh_args root@$VIRTHOST "cd $virthost_source_location && chmod +x build-images.sh && delorean_current_hash=$delorean_current_hash ./build-images.sh"
