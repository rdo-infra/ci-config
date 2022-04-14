#artifact_promoter

Role to promote file artifacts for a given candidate and target label.

## Variables

* `promotion_type`: (String) Promotion type to be performed. Default: 'file'. Choices: 'file', 'centos-compose'.
* `remote_server`: (String) Host or IP of the server to store the compose-ids. Default: '127.0.0.1'
* `remote_port`: (String) TCP destination port to be used on SSH connection with the remote server. Default: '22'
* `remote_user`: (String) User to be used on SSH connection with the remote server. Default: '${USER}'
* `remote_key_path`: (String) Absolute path to the private key to be used by the SSH client. Default: '~/.ssh/id_rsa'
* `remote_working_dir`: (String) Path to the working directory (in the remote server) where artifacts and labels should be created. Default: '${HOME}'
* `promotion_candidate_label`: (String) Candidate label of compose promotion. Default: ""
* `promotion_target_label`: (String) Target label of compose promotion. Default: 'centos-ci-testing
* `compose_promoter_latest_compose_url`: (String) URL used by the promoter get latest compose-id value. Default: 'https://composes.centos.org/latest-CentOS-Stream-8/COMPOSE_ID'
* `promotion_file_name`: (String) File name to be created in remote server. Mandatory if 'promotion_type' is set to 'file'. Default: "".
* `promotion_file_content` (String) File content to be written in promoted file artifact. Mandatory if 'promotion_type' is set to 'file'. Default: "".

Example 1:
```yaml
- hosts: all
  tasks:
    - name: Promote CentOS compose artifict - candidate latest-compose
      import_role:
        name: artifact_promoter
      vars:
        promotion_type: "centos-compose"
        remote_server: "127.0.0.1"
        remote_key_path: "~/.ssh/id_rsa"
        compose_promoter_latest_compose_url: "https://composes.centos.org/latest-CentOS-Stream-8/COMPOSE_ID"
        promotion_candidate_label: "latest-compose"
        promotion_target_label: "centos-ci-testing"
```

Example 2:
```yaml
- hosts: all
  tasks:
    - name: Promote generic file artifict
      import_role:
        name: artifact_promoter
      vars:
        promotion_type: "file"
        remote_server: "127.0.0.1"
        remote_key_path: "~/.ssh/id_rsa"
        promotion_file_name: "test_file_name"
        promotion_file_content: "test_file_content"
        promotion_target_label: "current-test"
```
