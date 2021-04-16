set -e
export RDO_VERSION='centos8-victoria'
export DELOREAN_HOST='trunk-primary.rdoproject.org'
export DELOREAN_PUBLIC_HOST='trunk.rdoproject.org'
export DELOREAN_URL="https://$DELOREAN_PUBLIC_HOST/centos8-victoria/current-tripleo/delorean.repo"
# The softlinks used in promotion should be cumulative. This job starts w/ current-tripleo
# If the job passes at the rdo level, rdo is appended to the new softlink name.
# End result would be two seperate softlinks e.g. current-tripleo, and current-tripleo-rdo
export LINKNAME='current-tripleo-rdo'
export LAST_PROMOTED_URL="https://$DELOREAN_PUBLIC_HOST/centos8-victoria/$LINKNAME/delorean.repo"
export RDO_VERSION_DIR='victoria'
# The LOCATION var is handed off to the ansible-role-tripleo-image build (atrib) role to define where testing/staged images are uploaded
export LOCATION='current-tripleo'
# The BUILD_SYS var stores what build system was used. It becomes part of the
# path where images are stored.
export BUILD_SYS='delorean'
# When ENABLE_PUPPET_MODULES_RPM is true, puppet modules are installed from
# rpm instead of git repo in p-o-i jobs
export ENABLE_PUPPET_MODULES_RPM=true
export IMAGE='template-rdo-centos8-stream'
export ANSIBLE_PYTHON_INTERPRETER='/usr/libexec/platform-python'
export HASH_FILE='/tmp/delorean_victoria_current_tripleo_hash'
