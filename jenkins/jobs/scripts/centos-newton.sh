set -e
export RDO_VERSION='centos-newton'
export DELOREAN_HOST='trunk-primary.rdoproject.org'
export DELOREAN_PUBLIC_HOST='trunk.rdoproject.org'
export DELOREAN_URL="http://$DELOREAN_HOST/centos7-newton/consistent/delorean.repo"
export LINKNAME='current-passed-ci'
export LAST_PROMOTED_URL="http://$DELOREAN_HOST/centos7-newton/$LINKNAME/delorean.repo"
export RDO_VERSION_DIR='newton'
# The LOCATION var is handed off to the atrib role to define where testing/staged images are uploaded
# centos-newton is using the "consistent" soft link in trunk-primary.
# This image is never used outside of CI. RDO TripleO users should only ever use content that was also
# vetted by TripleO-CI
export LOCATION='consistent'
export HASH_FILE='/tmp/delorean_newton_hash'
