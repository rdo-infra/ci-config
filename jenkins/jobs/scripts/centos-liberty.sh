set -e
export RDO_VERSION='centos-liberty'
export DELOREAN_HOST='trunk-primary.rdoproject.org'
export DELOREAN_PUBLIC_HOST='trunk.rdoproject.org'
export DELOREAN_URL="http://$DELOREAN_HOST/centos7-liberty/consistent/delorean.repo"
export LINKNAME='current-passed-ci'
export LAST_PROMOTED_URL="http://$DELOREAN_HOST/centos7-liberty/$LINKNAME/delorean.repo"
export RDO_VERSION_DIR='liberty'
export HASH_FILE='/tmp/delorean_liberty_hash'
