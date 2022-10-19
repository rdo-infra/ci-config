Infra Playbooks
===============

Playbooks in this [directory](https://github.com/rdo-infra/ci-config/tree/master/ci-scripts/infra-setup/) are used to setup infrastructure around
tripleo-ci. These playbooks have different tasks for setup and teardown
infrastructure.

Use [full-run.yml](https://github.com/rdo-infra/ci-config/blob/master/ci-scripts/infra-setup/full-run.yml) to setup infrastructure. It removes all running instances from Openstack, and creates new ones.

WARNING: `full-run.yml` will destroy all vms in the openstack instance.


Infrastructure setup/teardown playbooks use Ansible roles which are defined in the `roles/` directory.

Hosts
=====
`server_provision` role will provision three VMs in cloud.
- Promoter VM: For running promoter server.
- Toolbox VM: For running Tripleo CI related scripts. Ex. OVB cleanup scripts.
- RRCockpit VM: For Grafana dashboard.

Note: Modify `tenant_vars/infra-tripleo/servers.yml` to add more VMs.

Roles
=====
  - _ensure_credentials: Export credentials for promoter server.
  - _ensure_staging: Setup promoter staging environments for promoter.
  - general_teardown: To remove all networks/keypairs/images from openstack.
  - keypair: Create new openstack keypair.
  - promoter: To setup promoter server.
  - artifact_promoter: Role to promote file artifacts for a given candidate and target label.
  - server_provision: To provision machines in openstack.
  - servers_teardown: To delete machines in openstack.
  - ssh_agent: To setup new key with ssh agent.
  - setup_docker_compose: Setup docker compose on remote host
  - tenant_networks: To create networks and subnets in openstack.

User SSH Keys
=============

To login on deployed servers, add your ssh key in `tenant_vars/common.yaml`

Default Infra metadata
======================

Openstack needs to pass name and values while provisioning network, keypairs, security groups etc.
All those server configuration is stored in appropriate roles for `tenant_network`, `security_groups`, etc.
to provision machines on Vexxhost.

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
