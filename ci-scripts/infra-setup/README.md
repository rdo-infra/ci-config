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

Roles
=====
  - _ensure_credentials: Export credentials for promoter server.
  - _ensure_staging: Setup promoter staging environments for promoter.
  - base: This role will setup all basic requirements for servers like users, groups etc.
  - general_teardown: To remove all networks/keypairs/images from openstack.
  - keypair: Create new openstack keypair.
  - promoter: To setup promoter server.
  - artifact_promoter: Role to promote file artifacts for a given candidate and target label.
  - servers_provision: To provision machines in openstack.
  - servers_teardown: To delete machines in openstack.
  - ssh_agent: To setup new key with ssh agent.
  - setup_docker_compose: Setup docker compose on remote host
  - tenant_networks: To create networks and subnets in openstack.

  - configure_ssh: removes ssh access to default user: `cloud-user`
  - configure_continuous_delivery: setup continuous delivery script, which is going to pull necessary updates
  - configure_journalctl: enables persistent journalctl
  - configure_groups: configures default "tripleo" group
  - configure_users: creates users and adds their ssh keys
  - configure_packages: installs required packages on newly provisioned servers

  - configure_deployment_keypair: creates temporary deployment keypair for provisioning purposes

User SSH Keys
=============

To login on deployed servers, add your ssh key in `inventory/group_vars/all.yml`

Default Infra metadata
======================

Openstack needs to pass name and values while provisioning network, keypairs, security groups etc. All those server configuration is stored in `inventory/group_vars/vexxhost`, to provision machines on Vexxhost.

Set credentials for server `inventory/group_vars/vexxhost/secrets_example.yml`.

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


Deployment process
==================

Deployment process relies on presence of several configuration files in `inventory/group_vars/*` subdirectories.
Subdirectories should be named based on OpenStack cloud where infrastructure is planning to be deployed.
Currently there are two configurations:
  - vexxhost: configuration for default deployment of TripleO CI Infrastructure in Vexxhost project `infra_tripleo`
  - rhos_dev_stage: staging environment in PSI project `rhos_dev_stage` to test changes before merging them.

For appropriate RC files, please refer to appropriate cloud environments.
Deployment can be performed with:

    ansible-playbook -vvv -i inventory/ -e cloud="vexxhost" provision-all.yml


OpenStack Inventory
===================

To interact with OpenStack Inventory we're using [`openstack_inventory.py`](https://docs.ansible.com/ansible/latest/inventory_guide/intro_dynamic_inventory.html#explicit-use-of-openstack-inventory-script) script.
It is copy of upstream file, which is part of [ansible-collections-openstack](https://github.com/openstack/ansible-collections-openstack/blob/master/scripts/inventory/openstack_inventory.py)


Updated deployment process
====================================

TripleO Infrastructure is built on top of an OpenStack Environment. Infrastructure is installed with the use of Ansible playbooks.
To allow for decoupling of cloud configuration (creating networks, servers, etc.) from servers configuration (installation of packages,
deploying services, etc.), "rhos_dev_stage" environment is being changed to accomodate necessary updates. When updated deployment process will be proven working, it will become default deployment strategy.

Each configuration step is described by a separate playbook:
  - 1_deploy_infra.yml: configures required cloud environment, deploys necessary servers
  - 2_configure_infra.yml: runs installation and initial configuration of servers
  - 3_continuous_infra.yml: playbook which is being executed on the servers, to provide continuous updates.

Deployment can be performed with:

    ansible-playbook -i openstack_inventory.py -i inventory/ -e cloud="rhos_dev_stage" 1_deploy_infra.yml 2_configure_infra.yml
