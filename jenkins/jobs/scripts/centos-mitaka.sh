set -e
export RDO_VERSION='centos-mitaka'
export DELOREAN_HOST='trunk-primary.rdoproject.org'
export DELOREAN_PUBLIC_HOST='trunk.rdoproject.org'
export DELOREAN_URL="http://$DELOREAN_HOST/centos7-mitaka/consistent/delorean.repo"
export LINKNAME='current-passed-ci'
export LAST_PROMOTED_URL="http://$DELOREAN_HOST/centos7-mitaka/$LINKNAME/delorean.repo"
export RDO_VERSION_DIR='mitaka'
# The LOCATION var stores what repo symlink was used. It becomes part of the
# path where images are stored.
export LOCATION='consistent'
# The BUILD_SYS var stores what build system was used. It becomes part of the
# path where images are stored.
export BUILD_SYS='delorean'
export HASH_FILE='/tmp/delorean_mitaka_hash'
