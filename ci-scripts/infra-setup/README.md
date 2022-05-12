Infra Playbooks
===============

Playbooks in this diretory are used to setup infrastracture around
tripleo-ci. This playbooks have differnt tasks for setup and teardown
infra.

To setup infrastracture you can use `full-run.yml` playbooks, it will
teardown if there are any other instances running in openstack. And provision
new instances.


Infra playbooks uses different roles which are defined in the `roles/` directory.

Those roles have differnt tasks to perform.
  - _ensure_credentials: It will export credentials for promoter server.
  - _ensure_staging: Setup promoter staging environments for promoter.
  - base: This role will setup all basic requirements for servers like users, groups etc.
  - general_teardown: To remove all networks/keypairs/images from openstack.
  - keypair: Create new openstack keypair.
  - promoter: To setup promoter server.
  - promote_artifact: Role to promote ile artifacts for a given candidate and target label.
  - servers_provision: To provision machine in openstack.
  - servers_teardown: To delete macine in openstack.
  - ssh_agent: To setup new key with ssh agent.
  - setup_docker_compose: Setup docker compose on remote host
  - tenant_networks: To create networks and subnet in openstack.


To prepare the environment for deployment:

    cd /tmp/
    git clone https://review.rdoproject.org/r/p/rdo-infra/ci-config.git
    virtualenv deploy
    source deploy/bin/activate
    pip install ansible shade
    cd ci-config/ci-scripts/infra-setup
    export ANSIBLE_ROLES_PATH=$PWD/roles
    source <cloud-credentials>
    cd tests
    ./full-run.sh

To tear down everything:

    ./nuke.sh
