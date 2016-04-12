set -e
export RDO_VERSION='centos-mitaka'
export DELOREAN_HOST='trunk-primary.rdoproject.org'
export DELOREAN_URL="http://$DELOREAN_HOST/centos7-mitaka/consistent/delorean.repo"
export LAST_PROMOTED_URL="http://$DELOREAN_HOST/centos7-mitaka/current-passed-ci/delorean.repo"
export RDO_VERSION_DIR='mitaka'
export HASH_FILE='/tmp/delorean_mitaka_hash'