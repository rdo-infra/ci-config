#compose_promoter

Role to promote a CentOs Compose-ID for a given candidate and target label.

## Variables
* `compose_promoter_host`: (String) Host or IP of the server that store the compose-ids. Default: '127.0.0.1'
* `compose_promoter_port`: (String) Destination port to be used on SSH connection. Default: ''
* `compose_promoter_user`: (String) User to be used on SSH connection. Default: ''
* `compose_promoter_key_path`: (String) Absolute path to the private key to be used on SSH client. Default: ''
* `compose_promoter_working_dir`: (String) Path to the working directory where artifacts and labels should be created. Default: '{{ ansible_user_dir }}/workspace'
* `compose_promoter_distro`: (String) Target distro used when retrieving Compose-ID from URL. Default: ''
* `compose_promoter_compose_url`: (String) URL used by the promoter get latest compose-id value. Default: ''
* `compose_promoter_candidate_label`: (String) Candidate label of compose promotion. Default: 'latest-compose'
* `compose_promoter_target_label`: (String) Target label of compose promotion. Default: 'tripleo-ci-testing

Example:
```yaml
- hosts: all
  tasks:
    - name: Promote latest compose-id
      import_role:
        name: compose_promoter
      vars:
        compose_promoter_candidate_label: 'latest-compose'
        compose_promoter_target_label: 'tripleo-ci-testing'
```
