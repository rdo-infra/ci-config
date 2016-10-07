set -e
export RDO_VERSION_DIR='newton'
# The LOCATION var stores what repo symlink was used. It becomes part of the
# path where images are stored.
export LOCATION='cloudsig-stable'
# The BUILD_SYS var stores what build system was used. It becomes part of the
# path where images are stored.
export BUILD_SYS='cbs'
export HASH_FILE='/tmp/cloudsig-stable_newton_hash'
