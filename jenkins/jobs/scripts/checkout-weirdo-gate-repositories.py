#!/usr/bin/env python
#   Copyright Red Hat, Inc. All Rights Reserved.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

# A script to checkout a core ansible project and it's roles with ongoing reviews
# in an environment without zuul-cloner :(

import os
import sh

GERRIT_URL = "https://review.gerrithub.io/"
GERRIT_PROJECT = os.getenv('GERRIT_PROJECT')
GERRIT_REFSPEC = os.getenv('GERRIT_REFSPEC')

CORE_MAP = {
    'redhat-openstack/weirdo': 'weirdo'
}

ROLE_MAP = {
    'redhat-openstack/ansible-role-ci-centos': 'weirdo/playbooks/roles/ci-centos',
    'redhat-openstack/ansible-role-weirdo-common': 'weirdo/playbooks/roles/common',
    'redhat-openstack/ansible-role-weirdo-kolla': 'weirdo/playbooks/roles/kolla',
    'redhat-openstack/ansible-role-weirdo-packstack': 'weirdo/playbooks/roles/packstack',
    'redhat-openstack/ansible-role-weirdo-puppet-openstack': 'weirdo/playbooks/roles/puppet-openstack'
}


def clone_project(project, path):
    project_url = "{0}/{1}".format(GERRIT_URL, project)
    sh.git.clone(project_url, path)


def checkout_review(project, path):
    project_url = "{0}/{1}".format(GERRIT_URL, project)
    git_dir = "--git-dir={0}/.git".format(path)
    sh.git.fetch(git_dir, project_url, GERRIT_REFSPEC)
    sh.git.checkout(git_dir, "FETCH_HEAD")

if __name__ == '__main__':
    # Clone core(s), role(s) and checkout review if need be
    for project, path in CORE_MAP.items() + ROLE_MAP.items():
        clone_project(project, path)
        if project == GERRIT_PROJECT:
            checkout_review(project, path)
