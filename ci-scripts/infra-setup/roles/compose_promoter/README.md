#compose_promoter

Role to promote a CentOs Compose-ID for a given candidate and target label.

## Variables
* `compose_promoter_host`: (String) Host or IP of the server to store the compose-ids. Default: '127.0.0.1'
* `compose_promoter_port`: (String) TCP destination port to be used on SSH connection with the remote server. Default: '22'
* `compose_promoter_user`: (String) User to be used on SSH connection with the remote server. Default: '${USER}'
* `compose_promoter_key_path`: (String) Absolute path to the private key to be used by the SSH client. Default: '~/.ssh/id_rsa'
* `compose_promoter_working_dir`: (String) Path to the working directory (in the remote server) where artifacts and labels should be created. Default: '${HOME}'
* `compose_promoter_distro`: (String) Target distro used when retrieving latest Compose-ID from URL. Default: 'centos-stream-8'
* `compose_promoter_latest_compose_url`: (String) URL used by the promoter get latest compose-id value. Default: 'https://composes.centos.org/latest-CentOS-Stream-8/COMPOSE_ID'
* `compose_promoter_candidate_label`: (String) Candidate label of compose promotion. Default: 'latest-compose'
* `compose_promoter_target_label`: (String) Target label of compose promotion. Default: 'centos-ci-testing

Example:
```yaml
- hosts: all
  tasks:
    - name: Promote latest compose-id
      import_role:
        name: compose_promoter
      vars:
        compose_promoter_server: "127.0.0.1"
        compose_promoter_key_path: "~/.ssh/id_rsa"
        compose_promoter_latest_compose_url: "https://composes.centos.org/latest-CentOS-Stream-8/COMPOSE_ID"
        compose_promoter_candidate_label: 'latest-compose'
        compose_promoter_target_label: 'centos-ci-testing'
```
