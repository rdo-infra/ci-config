Promoter Server
===============

## Installation

- Requirements:
  - CentOS-8 box
  - 100GB storage

- Promoter server can be installed using Ansible playbooks. Promoter server can be deployed using different roles as per
  user need.

Ansible Roles
  - base: This role will create users and groups.
  - dns: Configure and run dnsmsq service.
  - promoter: This role will deploy promoter server.
  - sova:
  - rcockpit:
  - incockpit:

- To install and configure:
  ```shell
  ansible-playbook ci-config/ci-scripts/infra-setup/servers_setup.yaml
  ```
  It will configure box to run promoter server.

## Configuration

- Promoter server configuration now support for yaml file. To configure release file check below example
  ```yaml
  ---
  release: ussuri
  api_url: https://trunk.rdoproject.org/api-centos8-ussuri
  base_url: https://trunk.rdoproject.org/centos8-ussuri/
  distro_name: centos
  distro_version: 8
  dlrn_api_host: "trunk.rdoproject.org"
  # dlrn_api_endpoint: "centos8-ussuri"
  dlrn_api_scheme: "https"
  dlrn_api_port: ""
  promotions:
    current-tripleo:
      candidate_label: tripleo-ci-testing
      criteria:
        # Jobs to be added as they are defined and qualified
        # - periodic-tripleo-centos-8-ussuri-containers-build-push
        - periodic-tripleo-centos-8-buildimage-overcloud-full-ussuri
        - periodic-tripleo-centos-8-buildimage-ironic-python-agent-ussuri
        - periodic-tripleo-ci-centos-8-standalone-ussuri
        - periodic-tripleo-ci-centos-8-scenario001-standalone-ussuri
        - periodic-tripleo-ci-centos-8-scenario002-standalone-ussuri
        - periodic-tripleo-ci-centos-8-scenario003-standalone-ussuri

  current-tripleo-rdo:
      candidate_label: current-tripleo
      criteria:
        # Not ready for CentOS8 yet, uncomment once ready
        - tripleo-quickstart-promote-ussuri-current-tripleo-delorean-minimal
        - weirdo-ussuri-promote-packstack-scenario001
        - weirdo-ussuri-promote-packstack-scenario002
        - weirdo-ussuri-promote-packstack-scenario003
  ```

- `release`:  Release
- `api_url`: DLRN api url
- `base_url`: DLRN base url
- `distro_name`: Distribution which you are using
- `distro_version`: Distribution version, like 7, 8, 9 etc.
- `dlrn_api_host`: Hostname where DLRN is hosted (optional if base_url is specified)
- `dlrn_api_endpoint`: DLRN endpoint (optional if base_url is speificed)
- `dlrn_api_scheme`: DLRN scheme (‘http/https’) (optional if base_url is specified)
- `dlrn_api_port`: DLRN host port (optional if base_url is specified)
- `promotions`: This section will define promotion source, target and criteria
  - `current-tripleo`: Target name.
  - `candidate-label`: Source label, this will be promotion candidate.
  - `criteria`: This will be Zuul jobs list. DLRN promoter server will check all the jobs which got passed against candidate hash.

Configuration files can be put in the `ci-config/ci-script/dlrnapi_promoter/config_environments/rdo/CentOS-8/`.  Promoter server will access those files and proceed with the promotion. Default file location can be changed in `ci-scripts/dlrnapio_promoter/config_environments/global_defaults.yaml`

Some default values for the promoter server can be added to the defaults.yaml under rdo directory.

## Promotions

- TripleO promotion server has 3 promotion tasks
  - DLRN Hash Promotion
  - Container promotion
  - Qcow promotion



- DLRN Hash promotion

  DLRN Hash promotion can promote only dlrn packages with specific hash. All the clients can be enabled by adding in the defaults.yaml or can be enabled passing parameter to the dlrnapi_promoter.py command.

```shell
$ python3 dlrnapi_promoter.py --release-config CentOS-8/master.yaml \
  force-promote --allowed-client dlrn_client
```

- Container promotion

Container promotion promote containers from source registry to target registry. Source and target registry can be same or different. During container promotion containers can be pulled from source registry tagged with latest hash and promotion target name.

```shell
$ python3 dlrnapi_promoter.py --release-confing CentOS-8/master.yaml \
  force-promote --allowed-client registry_client
```

- QCow Promotion

  QCow promotion will promote QCow images. It will upload the images to the image server.

```shell
$ python3 dlrnapi_promoter --release-config CentOS-8/master.yaml \
  force-promote --allowed-client qcow_client
```

## Automated jobs validation
- Automated jobs validation can be performed using `validate_config_jobs.py` file.
```shell
python3 validate_config_jobs.py -c config_environments/rdo
```
