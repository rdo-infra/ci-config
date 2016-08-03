set -e
export RDO_VERSION='centos-master'
export DELOREAN_HOST='trunk-primary.rdoproject.org'
export DELOREAN_URL="http://$DELOREAN_HOST/centos7-new/consistent/delorean.repo"
export LAST_PROMOTED_URL="http://$DELOREAN_HOST/centos7-new/current-passed-ci/delorean.repo"
export RDO_VERSION_DIR='new'
export HASH_FILE='/tmp/delorean_new_hash'
