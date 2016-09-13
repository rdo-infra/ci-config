set -e
export RDO_VERSION='centos-master'
export DELOREAN_HOST='trunk-primary.rdoproject.org'
export DELOREAN_PUBLIC_HOST='trunk.rdoproject.org'
export DELOREAN_URL="http://$DELOREAN_HOST/centos7-master/consistent/delorean.repo"
export LINKNAME='puppet-passed-ci'
export LAST_PROMOTED_URL="http://$DELOREAN_HOST/centos7-master/$LINKNAME/delorean.repo"
export HASH_FILE='/tmp/delorean_puppet_hash'

# If delorean_current_hash is not set, it means the job hasn't sourced the HASH_FILE
# Source it.
[[ -z "${delorean_current_hash}" ]] && source ${HASH_FILE}
