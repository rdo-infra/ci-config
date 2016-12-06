set -eux

pushd $WORKSPACE

git clone https://github.com/rdo-infra/ci-config
git clone https://github.com/openstack/tripleo-quickstart

bash tripleo-quickstart/ci-scripts/get-node.sh

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
ssh $ssh_args root@$VIRTHOST "cd $virthost_source_location && chmod +x build-images.sh && ./build-images.sh"

