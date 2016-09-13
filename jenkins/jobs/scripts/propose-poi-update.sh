#!/bin/bash -xe
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# Adapted and simplified from upstream:
# https://github.com/openstack-infra/project-config/blob/c0a7436c330da0970e829be2e416bfc2bcf36c48/jenkins/scripts/propose_update.sh

# This script is used to create reviews in openstack/puppet-openstack-integration
# when there is a failure in testing a specific dlrn hash

INITIAL_COMMIT_MSG="RDO Trunk CI: Failed puppet-openstack-integration promotion"
TOPIC="openstack/puppet/rdo"
BRANCH="master"
USERNAME="rdothirdparty"
PROJECT="openstack/puppet-openstack-integration"
PROJECT_DIR="$(basename ${PROJECT})"
GIT_REPO_URL="git://git.openstack.org/${PROJECT}.git"
TESTED_HASH="${delorean_current_hash}"

# Ensure dependencies are installed
yum -y install git epel-release
yum -y install git-review

rm -rf ${PROJECT_DIR}
git clone ${GIT_REPO_URL} ${PROJECT_DIR}

pushd ${PROJECT_DIR}
CURRENT_HASH=$(egrep -o "'(https://trunk.rdoproject.org.*)'" manifests/repos.pp |awk -F '/' '{ print $5"/"$6"/"$7 }')
sed -i -e "s%$CURRENT_HASH%$TESTED_HASH%" manifests/repos.pp
setup_git
setup_commit_message ${PROJECT} ${USERNAME} ${BRANCH} ${TOPIC} "${INITIAL_COMMIT_MSG}"
git review -s

if ! git diff --stat --exit-code HEAD ; then
    # Commit and review
    git_args="-a -F-"
    git commit $git_args <<EOF
$COMMIT_MSG
EOF
    # Do error checking manually to ignore one class of failure.
    set +e
    OUTPUT=$(git review -t $TOPIC $BRANCH)
    RET=$?
    [[ "$RET" -eq "0" || "$OUTPUT" =~ "no new changes" || "$OUTPUT" =~ "no changes made" ]]
    SUCCESS=$?
    set -e
fi
popd
exit $SUCCESS
