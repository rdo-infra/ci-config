Infra Playbooks
===============

Playbooks in this [directory](https://github.com/rdo-infra/ci-config/tree/master/ci-scripts/infra-setup/) are used to setup infrastracture around
tripleo-ci. These playbooks have different tasks for setup and teardown
infrastracture.

To setup infrastructure you can use [full-run.yml](https://github.com/rdo-infra/ci-config/blob/master/ci-scripts/infra-setup/full-run.yml) playbooks, it will
teardown if there are any other instances running in openstack. And provision
new instances.

WARNING: `full-run.yml` will destory all vms in the openstack instance.


Infrastracture setup/teardown playbooks uses Ansible roles which are defined in the `roles/` directory.

Roles:
  - _ensure_credentials: Export credentials for promoter server.
  - _ensure_staging: Setup promoter staging environments for promoter.
  - base: This role will setup all basic requirements for servers like users, groups etc.
  - general_teardown: To remove all networks/keypairs/images from openstack.
  - keypair: Create new openstack keypair.
  - promoter: To setup promoter server.
  - artifact_promoter: Role to promote file artifacts for a given candidate and target label.
  - servers_provision: To provision machine in openstack.
  - servers_teardown: To delete machine in openstack.
  - ssh_agent: To setup new key with ssh agent.
  - setup_docker_compose: Setup docker compose on remote host
  - tenant_networks: To create networks and subnet in openstack.

User SSH Keys
=============

To login on deployed servers, add your ssh key in `tenant_vars/common.yaml`

Default Infra metadata
======================

Openstack needs to pass name and values while provisioning network, keypairs security groups
etc. All those server configuration metadata is stored in `tenant_vars/infra-tripleo`. This is only for setup infra on Vexxhost.

Set credentials for server `tenant_vars/infra-tripleo/secrets_example.yml`.

To prepare the environment for deployment:

    cd /tmp/
    git clone https://review.rdoproject.org/r/p/rdo-infra/ci-config.git
    virtualenv deploy
    source deploy/bin/activate
    pip install ansible openstacksdk
    cd ci-config/ci-scripts/infra-setup
    export ANSIBLE_ROLES_PATH=$PWD/roles
    source <cloud-credentials>
    cd tests
    ./full-run.sh

To teardown everything:

    ./nuke.sh
