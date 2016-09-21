set -e
export RDO_VERSION_DIR='newton'
# The LOCATION var stores what repo symlink was used. It becomes part of the
# path where images are stored.
export LOCATION='consistent'
# The BUILD_SYS var stores what build system was used. It becomes part of the
# path where images are stored.
export BUILD_SYS='cloudsig-testing'
export HASH_FILE='/tmp/cloudsig-testing_newton_hash'
