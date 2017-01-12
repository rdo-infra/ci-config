set -e
export RDO_VERSION_DIR='mitaka'
# The LOCATION var stores what repo symlink was used. It becomes part of the
# path where images are stored.
export LOCATION='cloudsig-stable'
# The BUILD_SYS var stores what build system was used. It becomes part of the
# path where images are stored.
export BUILD_SYS='cbs'
export HASH_FILE='/tmp/cloudsig-stable_mitaka_hash'
export RERUN_ON_SAME_HASH=0
