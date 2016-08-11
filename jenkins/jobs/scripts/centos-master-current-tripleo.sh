set -e
export RDO_VERSION='centos-newton'
export DELOREAN_HOST='trunk-primary.rdoproject.org'
export DELOREAN_URL="http://$DELOREAN_HOST/centos7-master/current-tripleo/delorean.repo"
# The softlinks used in promotion should be cumulative. This job starts w/ current-tripleo
# If the job passes at the rdo level, rdo is appended to the new softlink name.
# End result would be two seperate softlinks e.g. current-tripleo, and current-tripleo-rdo
export LINKNAME='current-tripleo-rdo'
export LAST_PROMOTED_URL="http://$DELOREAN_HOST/centos7-master/$LINKNAME/delorean.repo"
export RDO_VERSION_DIR='master'
# The LOCATION var is handed off to the ansible-role-tripleo-image build (atrib) role to define where testing/staged images are uploaded
export LOCATION='testing'
export HASH_FILE='/tmp/delorean_master_current_tripleo_hash'
