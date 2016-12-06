#!/bin/bash

set -eux

curl -o centos.qcow2 http://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2

sudo yum install -y libguestfs-tools

# Create build script
cat <<EOS > build-images-vc.sh
#!/bin/bash
# virt-customize script to build master overcloud and ipa images in an isolated environment

set -eux

# NOTE(trown): DIB expects /dev/pts to exist and libguestfs is not mounting the guest with it
# so we just manually mount it in the guest
# This will be fixed when https://www.redhat.com/archives/libguestfs/2016-December/msg00024.html
# is available in CentOS version of libguestfs
mkdir /dev/pts
mount devpts /dev/pts -t devpts

curl -Lo /etc/yum.repos.d/delorean.repo \
http://trunk.rdoproject.org/centos7-master/$delorean_current_hash/delorean.repo

curl -Lo /etc/yum.repos.d/delorean-deps.repo \
http://trunk.rdoproject.org/centos7-master/delorean-deps.repo

yum install -y yum-plugin-priorities

# Enable Storage/SIG Ceph repo
rpm -q centos-release-ceph-jewel || sudo yum -y install --enablerepo=extras centos-release-ceph-jewel
sudo sed -i -e 's%gpgcheck=.*%gpgcheck=0%' /etc/yum.repos.d/CentOS-Ceph-Jewel.repo

yum update -y

yum -y install python-tripleoclient

export DIB_YUM_REPO_CONF="\$(ls /etc/yum.repos.d/delorean*) /etc/yum.repos.d/CentOS-Ceph-Jewel.repo"

openstack overcloud image build \
  --config-file /usr/share/tripleo-common/image-yaml/overcloud-images-centos7.yaml \
  --config-file /usr/share/tripleo-common/image-yaml/overcloud-images.yaml

EOS

# Build images using virt-customize for isolation from build host
sudo LIBGUESTFS_BACKEND=direct \
virt-customize -m 16000 --smp 4 -a centos.qcow2 --run build-images-vc.sh

# Extract images from isolated env
copy_out_cmd='sudo LIBGUESTFS_BACKEND=direct virt-copy-out -a centos.qcow2'
$copy_out_cmd /ironic-python-agent.initramfs .
$copy_out_cmd /ironic-python-agent.vmlinuz .
$copy_out_cmd /overcloud-full.qcow2 .
$copy_out_cmd /overcloud-full.initrd .
$copy_out_cmd /overcloud-full.vmlinuz .

# TODO(trown) extract logs as well.
# For now just touch the files CI expects to be there
touch artib-logs.tar.gz artib-logs.tar.gz.md5


# Create undercloud from overcloud
cp overcloud-full.qcow2 undercloud.qcow2
qemu-img resize undercloud.qcow2 20G

cat <<EOS > convert-overcloud-vc.sh
#!/bin/bash

# Script to convert an overcloud-full.qcow2 to an undercloud.qcow2 via virt-customize
# Copied from https://github.com/openstack/tripleo-quickstart/blob/24437dd45e39dc1964aacf14dc5d73f5915ba3f5/roles/libvirt/setup/undercloud/templates/convert_image.sh.j2
# With added repo setup, since overcloud-full is built with DIB_YUM_REPO_CONF

set -eux

FS_TYPE=`findmnt -o FSTYPE -fn /`

if [ "\$FS_TYPE" = "xfs" ]; then
    xfs_growfs /
elif [ "\$FS_TYPE" = "ext4" ]; then
    resize2fs /dev/sda
else
    echo "ERROR: Unknown filesystem, cannot resize."
    exit 1
fi

curl -Lo /etc/yum.repos.d/delorean.repo \
http://trunk.rdoproject.org/centos7-master/$delorean_current_hash/delorean.repo

curl -Lo /etc/yum.repos.d/delorean-deps.repo \
http://trunk.rdoproject.org/centos7-master/delorean-deps.repo

yum install -y yum-plugin-priorities

# Enable Storage/SIG Ceph repo
rpm -q centos-release-ceph-jewel || sudo yum -y install --enablerepo=extras centos-release-ceph-jewel
sudo sed -i -e 's%gpgcheck=.*%gpgcheck=0%' /etc/yum.repos.d/CentOS-Ceph-Jewel.repo

yum update -y

yum remove -y cloud-init python-django-horizon openstack-dashboard
yum install -y python-tripleoclient
# NOTE(trown) Install tempest and test packages in a seperate yum transaction
# so that we do not fail the conversion if this install fails. There is a period
# after TripleO uploads a new image, but before the buildlogs repo gets synced,
# where this will fail because we try to install older test packages than the
# service packages already installed in the image.
yum install -y openstack-tempest python-aodh-tests python-ceilometer-tests \
python-heat-tests python-ironic-tests python-keystone-tests python-manila-tests \
python-mistral-tests python-neutron-tests python-sahara-tests python-zaqar-tests \
|| /bin/true

useradd stack
echo "stack ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/stack
chmod 0440 /etc/sudoers.d/stack

mkdir /home/stack/.ssh

echo "127.0.0.1  localhost undercloud" > /etc/hosts
echo "HOSTNAME=undercloud" >> /etc/sysconfig/network
echo "undercloud" > /etc/hostname

chown -R stack:stack /home/stack/

# Add a 4GB swap file to the Undercloud
dd if=/dev/zero of=/swapfile bs=1024 count=4194304
mkswap /swapfile
chmod 600 /swapfile
# Enable it on start
echo "/swapfile swap swap defaults 0 0" >> /etc/fstab

sed -i 's/SELINUX=enforcing/SELINUX=permissive/' /etc/selinux/config

EOS

sudo LIBGUESTFS_BACKEND=direct \
virt-customize -m 16000 --smp 4 -a undercloud.qcow2 --run convert-overcloud-vc.sh \
--upload ./ironic-python-agent.initramfs:/home/stack/ironic-python-agent.initramfs \
--upload ./ironic-python-agent.vmlinuz:/home/stack/ironic-python-agent.vmlinuz \
--upload ./overcloud-full.qcow2:/home/stack/overcloud-full.qcow2 \
--upload ./overcloud-full.initrd:/home/stack/overcloud-full.initrd \
--upload ./overcloud-full.vmlinuz:/home/stack/overcloud-full.vmlinuz \
--run-command 'chown stack:stack /home/stack/*'

# Sparsify the undercloud image
sudo LIBGUESTFS_BACKEND=direct \
virt-sparsify --tmp ./ \
--check-tmpdir fail \
--compress undercloud.qcow2 undercloud-compressed.qcow2

rm -f undercloud.qcow2
mv undercloud-compressed.qcow2 undercloud.qcow2

# tar and create md5s for all images
tar -cf ironic-python-agent.tar ironic-python-agent.initramfs ironic-python-agent.vmlinuz
tar -cf overcloud-full.tar overcloud-full.qcow2 overcloud-full.initrd overcloud-full.vmlinuz

md5sum ironic-python-agent.tar > ironic-python-agent.tar.md5
md5sum overcloud-full.tar > overcloud-full.tar.md5
md5sum undercloud.qcow2 > undercloud.qcow2.md5


