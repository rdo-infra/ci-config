set -e
export RDO_VERSION='centos-newton'
export DELOREAN_HOST='trunk-primary.rdoproject.org'
export DELOREAN_PUBLIC_HOST='trunk.rdoproject.org'
export DELOREAN_URL="http://$DELOREAN_HOST/centos7-newton/consistent/delorean.repo"
export LINKNAME='current-passed-ci'
export LAST_PROMOTED_URL="http://$DELOREAN_HOST/centos7-newton/$LINKNAME/delorean.repo"
export RDO_VERSION_DIR='newton'
# The LOCATION var stores what repo symlink was used. It becomes part of the
# path where images are stored.
export LOCATION='consistent'
# The BUILD_SYS var stores what build system was used. It becomes part of the
# path where images are stored.
export BUILD_SYS='delorean'
export TEMPEST_VERSION='origin/master'
export HASH_FILE='/tmp/delorean_newton_hash'
