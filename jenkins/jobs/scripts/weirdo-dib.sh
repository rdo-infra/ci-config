#!/bin/bash
set -ex
# Use diskimage-builder to generate a CentOS 7 image with pre-installed weirdo packages
WORKSPACE=${WORKSPACE:-/tmp}
TMPDIR=$(mktemp -d -p ${WORKSPACE})

echo "Building in ${WORKSPACE}..."
echo "Temporary directory is ${TMPDIR}..."

pushd $WORKSPACE
# Install dependencies
[[ ! -d dib_venv ]] && virtualenv dib_venv
source dib_venv/bin/activate
pip install diskimage-builder

# Set up passwordless sudo devuser element for a basic default user
export DIB_DEV_USER_USERNAME="centos"
export DIB_DEV_USER_PWDLESS_SUDO="yes"

# Set up ssh keys
export DIB_DEV_USER_AUTHORIZED_KEYS="${TMPDIR}/keys"
cat << EOF > ${DIB_DEV_USER_AUTHORIZED_KEYS}
ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAyJ4DxTKdQ8grli+FqUzoJnXWlwvhWBJwdSbKJh6en6tWwLp97dUXM2R8B5WGtggtlC7SKOSk0u49ZAOInz5lf4ljSStkWIm4DzwJWEKB5iiWgorEwhYyuKFvfikC2OMlPE8bBKCquK40gWGYeINMGeeoKWeXhB5ks4MjZqg0l65J3BGHJd4StDSd903lzNwPM9c8LBfHgEM0H7K1W/Qt86rDi2bcaDv1q1xNhVjQ8v/bR3yglnwsEjX5S6ULQlx3mYUMhfRQUiOb7bSaBlDL9faKL89GFrvkMT3zJ4v65cHpPDa3pQfuD/k+UBUhFeaXMyPFT/Wmimf2g7iLroCbhQ== rdo-ci@ci.centos.org
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCp9iFXvR6UoWYboU41KFpx+Sdd7ov0i+szIjdB7p8LAR5mjVCWZWAyUSE16DQO0VRbl6FpxFUPRQCUXg5P59D6MjRPB+lIvAyZ53CkgVfkaKYNdLQKRoyBR0Q5ng0Gt74AwU7fo0lyVa9MYsxAVbwrE0ngrqzGA1Lm5TSAmZeURZLch65xZm8qc5UU2TZ9f9NEwdZgKFAplBT2Om+DdECNO+TRy/RAivBFmZangQBnBEp4cOiverur22Lc2MO4veBVT+pvTWI0YNKFPmwRpgfWTsZ6R1sUOHCIXmK+P8nR/BMAF/+XXNdEg4RTJFCNP5nWiSUpMj3z6dvQ0zv1twgb nodepool@review.rdoproject.org
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDBH7d5MTSlwAKp8ejbd0GNq0YUVXIzSunGXhFigNgl1oqrTapJIsJ6aGv3p400al5YKWua3Z/DzNftkz8VfermnsWli6SJAhcYPY7SDMTlFXKyTKLbG+k917v1QdtA2g6RqlfvfGSfYj6VwA7bNKjosrceN6GI+9HqY9nLcclQZ1xCr+wNShpfQrqlYKYBnI6JG26c8HfE/H3vSHKRsry4cscx+BDTlurMPF72zdrNGvbbV6LMxY6gbLj3xrCof1GxjU0PbXEMBdePWMxFqRb9do8+iz5noHUUTIElGIpFA2z40mdZ5w1FQYt/rYa1ehNTO25nXXhFTYgn2Y+fQb25 dmsimard@hostname
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCwEtxKw9XCxQUsUsRDxOpSo8+9KpX8lOlL0q9owdAb3W2YHv5d4XSlkZ78h7hDORoGLbNFEILBWb3pOJ+uDn7u7EtpZlKYqlJh3diHYCZuUETpG5WBbUExfDLLolbDdiihJKD06Y6wu8vzaDZSxrRrMuRo1PjmzsHKtoV7qip5a+jnFqPtE+DHVh8GhZkY2Qhbji0+fv4JUSLvcrLEJUIE5XHLG0BniJsTQCu4R05rBzd2gfTet95B7LSw1dNObvIVb8dnJBCQ5IFKblOAZp3M0EKdjmNdSTjgLlorqMN1F0YMi6unrfimPyH5pzd1Rnf2Cr2gcT+M55hcueHp86Lh jpena@hostname
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDYmpEuiWLuUFftIu+vQQmTC8m86GkNQXeNlrY9TRZtVqMZXEgIQuf9jeHZ89nKRX1eoRXH1NGk59RDiYVqOpp1NHRj+v7JjvdB8bkTCKYqyltLANRMO0gq+YAFSV7xY4DPskBLXswxhMY/5yCP9jlnXp6tdHIMfaQpdR/DjrXFt5QwrvXBbYUXoJUh/tAozlvj2w/qu41GAFPPKJ+wzl4M46YaEO39yMSbTue/g1Vn2XNWtX5Ocx41CeNFjbW5ghSJuvFHtHLG3sxT7YTwY/TTXLaVwZu4RwQEHqs9bnS6U7OWxjOxAMPuNnn3aMO/fHFheUGmmYETTfKfLXEv54UVUCq4/uqcD1UHwoddG7lQpdUmHpEBusgBc2sj+1Ysrt5EZ29iWI55Ke6FIxESOW73ttDsbgD8QC+IX2X3dhzvzI/9lKMScyO+JhzhzG3aOO9+wqqt/89Xdq3775J3IgePiDlOzcbvjIOsfgqmuaz5hPeqPLMcVThonOgl1UarsHeppyLRqykcUB0LqgmM3CGSCQaDfHulZMGfk3WsOHmj4eqW+gt4flKbzzvrB0W8ZPyCmQumqDTwZeI7EVnuNlTVUpdLZNMEjmgidEEM5aGuweA88QexefWdWwC+H9UbyL1R95Ka4f1Ek8n1oI/321nlA7ur4hLcB/c10yvWkwlFRQ== apevec@hostname
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCzSWK0/apjniWnXflcSQE+XNFDc4bWvgWnhhXj++Woc9/O7w/TrPh+3GPh7YUaNX01DVB6YgXevGTN3qm1abrKDDhlUKfuI3HTACnrd8eZQhcoyJ/SQUspbnrbQXFDU9QEmPcvZqHXtkt0Y0ihfN04Y3ba1iYkHfysFqxMvJiwYzdOcV8JD5kULkvd5hXYRxj/rSHl1k83XwKwL6adtabhgzSrsxYhCJ0LzecGN+3l3vZvhkfzV6m8YgGFMS9UpXsLzk1rbwKr8zVnj4sTgk817kGqnyrEkbCYFfiOduDnkvTSY34bJ3+LW7dsgwOiKi9KyIFt9YqVYqnIR5xovMF1 amoralej@hostname
EOF

# This is a hack so we don't have to set up extra elements for something temporary
export DIB_LOCATION=$(python -c "import os,diskimage_builder; print(os.path.dirname(diskimage_builder.__file__))")
# Set up pre-installed package list and include them inside centos-minimal element
package_list="https://raw.githubusercontent.com/rdo-infra/review.rdoproject.org-config/master/nodepool/elements/rdo-base/package-installs.yaml"
curl -o ${TMPDIR}/package-installs.yaml -q -s ${package_list}
cp ${TMPDIR}/package-installs.yaml ${DIB_LOCATION}/elements/centos-minimal/
# Enable CentOS CR (Continuous Release) repository for upcoming 7.4
cat << EOF > ${DIB_LOCATION}/elements/centos-minimal/yum.repos.d/yum.repo
[base]
name=CentOS-\$releasever - Base
mirrorlist=http://mirrorlist.centos.org/?release=\$releasever&arch=\$basearch&repo=os&infra=\$infra
#baseurl=http://mirror.centos.org/centos/\$releasever/os/\$basearch/
gpgcheck=0
#gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7
enabled=1

[cr]
name=CentOS-\$releasever - cr
baseurl=http://mirror.centos.org/centos/\$releasever/cr/\$basearch/
gpgcheck=0
#gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7
enabled=1
EOF

disk-image-create -t raw -o centos7-weirdo \
    centos-minimal \
    simple-init \
    vm \
    growroot \
    pip-and-virtualenv \
    openssh-server \
    selinux-permissive \
    devuser
popd
