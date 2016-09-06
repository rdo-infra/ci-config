# usage: publish-testing-images.sh <RELEASE> <BUILD SYSTEM> <LOCATION>
RELEASE=$1
BUILD_SYS=$2
LOCATION=$3

mkdir -p testing

# get images from the virthost
scp_cmd='scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
for image in undercloud.qcow2 ironic-python-agent.tar overcloud-full.tar; do
    $scp_cmd root@$VIRTHOST:/var/lib/oooq-images/$image* ./testing/
done

# push images to ci.centos artifacts server
rsync -av testing/ rdo@artifacts.ci.centos.org::rdo/images/$RELEASE/$BUILD_SYS/$LOCATION/testing/

# push images to RDO file server
$scp_cmd testing/* images.rdoproject.org:/var/www/html/images/$RELEASE/$BUILD_SYS/$LOCATION/testing/

# remove images from jenkins slave
rm -rf testing