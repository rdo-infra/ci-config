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

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.compose_promoter import promoter

DOCUMENTATION = r'''
---
module: compose_promoter

short_description: Promote CentOS Compose-ID.
version_added: "1.0.0"
author: Douglas Viroel (@viroel)

description:
    - Promote CentOS Compose-ID from candidate label to target label,
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
    distro:
        description:
          - Distro used when retrieving Compose-ID from source URL.
        type: str
        choices: ['centos8']
    compose_url:
        description:
          - Full URL to be used by the promoter to get the latest compose-id.
        type: str
    candidate_label:
        description:
          - Compose-ID candidate label of a promotion.
        required: true
        type: str
        choices: ['latest-compose']
    target_label:
        description:
          - Compose-ID target label of a promotion.
        required: true
        type: str
        choices: ['tripleo-ci-testing']
'''

EXAMPLES = r'''
#
- name: Promote compose-id to tripleo-ci-testing in a remote server
  compose_promoter:
    server: 10.0.0.10
    user: centos
    distro: centos8
    private_key_path: ~/.ssh/id_rsa
    working_dir: /var/www/html/centos8
    candidate_label: latest-compose
    target_label: tripleo-ci-testing
'''

RETURN = r''' # '''


def run_module():
    # define available arguments/parameters a user can pass to the module
    target_label_choices = ['tripleo-ci-testing']
    candidate_label_choices = ['latest-compose']
    distro_choices = ['centos8']
    module_args = dict(
        server=dict(type='str', required=True),
        port=dict(type='str', default='22'),
        user=dict(type='str'),
        private_key_path=dict(type='str'),
        working_dir=dict(type='str', required=True),
        distro=dict(type='str', choices=distro_choices, default='centos8'),
        compose_url=dict(type='str'),
        candidate_label=dict(type='str', choices=candidate_label_choices,
                             required=True),
        target_label=dict(type='str', choices=target_label_choices,
                          required=True),
    )

    result = dict(
        changed=False,
        msg=''
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False
    )

    try:
        # 1. Create SFTP client
        _port = int(module.params['port']) if module.params['port'] else None
        sftp_client = promoter.SftpClient(
            hostname=module.params['server'],
            port=_port,
            user=module.params['user'],
            pkey_path=module.params['private_key_path']
        )

        # 2. Create promoter
        prom_obj = promoter.ComposePromoter(
            sftp_client,
            working_dir=module.params['working_dir'],
            distro=module.params['distro'],
            compose_url=module.params['compose_url'],
        )

        # 3. Promote
        prom_obj.promote(
            module.params['target_label'],
            candidate_label=module.params['candidate_label'],
        )
    except Exception as exc:
        result['msg'] = str(exc)
        module.fail_json(**result)

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
