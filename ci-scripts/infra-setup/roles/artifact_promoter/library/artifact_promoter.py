#!/usr/bin/python
#   Copyright 2021 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

from ansible.module_utils.artifact_promoter import (artifact_promoter,
                                                    compose_promoter)
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r'''
---
module: artifact_promoter

short_description: Promotes generic file artifacts.
version_added: "1.0.0"
author: Douglas Viroel (@viroel)

description:
    - Promote file artifacts from candidate label to target label,
      given an destination server and working directory.

options:
    server:
        description:
          - Hostname or IP of the server that stores artifacts and labels.
        required: true
        type: str
    port:
        description:
          - Destination port to be used when connection through SSH protocol.
        type: str
    user:
        description:
          - User name to be used by SSH client.
        type: str
    private_key_path:
        description:
          - Absolute path to a private key to be used by SSH client.
        type: path
    working_dir:
        description:
          - Path to the working directory where artifacts and labels should
            be created.
        required: true
        type: path
    promotion_type:
        description:
          - Type of artifact promotion to be made.
        required: true
        type: str
        choices: ['file', 'centos-compose']
    candidate_label:
        description:
          - Candidate label of a promotion.
        type: str
    target_label:
        description:
          - Target label of a promotion.
        required: true
        type: str
    file_name:
        description:
          - Filename to be created at destination server
        type: str
    file_content:
        description:
          - Content to be added into the file created at destination server.
        type: str
    latest_compose_url:
        description:
          - Full URL to be used by the promoter to get the latest compose-id.
        type: str
'''

EXAMPLES = r'''
#
- name: Promote a file content to target label in a remote server
  artifact_promoter:
    promotion_type: 'file'
    server: 10.0.0.10
    user: centos
    private_key_path: ~/.ssh/id_rsa
    working_dir: /var/www/html/latest
    target_label: current-centos
    file_name: 'fake_file_name'
    file_content: 'fake_file_content'

- name: Promote compose-id to centos-ci-testing in a remote server
  artifact_promoter:
    promotion_type: 'centos-compose'
    server: 10.0.0.10
    user: centos
    private_key_path: ~/.ssh/id_rsa
    working_dir: /var/www/html/centos8
    candidate_label: latest-compose
    target_label: centos-ci-testing
'''

RETURN = r''' # '''


def run_module():
    # define available arguments/parameters a user can pass to the module
    promotion_types = ['file', 'centos-compose']
    module_args = dict(
        server=dict(type='str', required=True),
        port=dict(type='str', default='22'),
        user=dict(type='str'),
        private_key_path=dict(type='str'),
        working_dir=dict(type='str', required=True),
        promotion_type=dict(type='str', required=True,
                            choices=promotion_types),
        candidate_label=dict(type='str', required=True),
        target_label=dict(type='str'),
        latest_compose_url=dict(type='str'),
        file_name=dict(type='str'),
        file_content=dict(type='str'),
    )

    result = dict(
        changed=False,
        msg=''
    )

    required_if_params = [
        ["candidate_label", "latest-compose", ["latest_compose_url"]],
        ["promotion_type", "file", ["file_name"]]
    ]

    module = AnsibleModule(
        argument_spec=module_args,
        required_if=required_if_params,
        supports_check_mode=False
    )

    # 1. Create SFTP client
    _port = int(module.params['port']) if module.params['port'] else None
    sftp_client = artifact_promoter.SftpClient(
        hostname=module.params['server'],
        port=_port,
        user=module.params['user'],
        pkey_path=module.params['private_key_path']
    )

    # 2. Create promoter
    if module.params['promotion_type'] == 'centos-compose':
        prom_obj = compose_promoter.ComposePromoter(
            sftp_client,
            module.params['working_dir'],
            compose_url=module.params['latest_compose_url'],
        )

        prom_obj.promote(
            module.params['target_label'],
            candidate_label=module.params['candidate_label'],
        )
    else:
        prom_obj = artifact_promoter.FileArtifactPromoter(
            sftp_client,
            module.params['working_dir'],
        )

        prom_obj.promote(
            module.params['target_label'],
            candidate_label=module.params['candidate_label'],
            artifact_name=module.params['file_name'],
            artifact_content=module.params['file_content'],
        )

    # Successful module execution
    result['changed'] = True
    result['msg'] = (
        "Successfully promoted compose-id from '%(candidate)s' to "
        "'%(target)s'" % {
            'candidate': module.params['candidate_label'],
            'target': module.params['target_label']
        })
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
