set -e
export RDO_VERSION='centos8-master-uc'
export DELOREAN_PUBLIC_HOST='trunk.rdoproject.org'
export DELOREAN_REPO='centos8-master'
# The softlinks used in promotion should be cumulative. This job starts w/ current-tripleo
# If the job passes at the rdo level, rdo is appended to the new softlink name.
# End result would be two seperate softlinks e.g. current-tripleo, and current-tripleo-rdo
export CANDIDATE_LINKNAME='current-tripleo'
export PROMOTED_LINKNAME='current-tripleo-rdo'
export RDO_VERSION_DIR='master'
# The LOCATION var is handed off to the ansible-role-tripleo-image build (atrib) role to define where testing/staged images are uploaded
export LOCATION='current-tripleo'
# The BUILD_SYS var stores what build system was used. It becomes part of the
# path where images are stored.
export BUILD_SYS='delorean'
# When ENABLE_PUPPET_MODULES_RPM is true, puppet modules are installed from
# rpm instead of git repo in p-o-i jobs
export ENABLE_PUPPET_MODULES_RPM=true
export HASH_FILE="$WORKSPACE/delorean_master_centos8_current_tripleo_hash"
export CICO_OS_RELEASE=8-stream
export ANSIBLE_PYTHON_INTERPRETER=/usr/libexec/platform-python
