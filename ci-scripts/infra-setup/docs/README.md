TripleO CI infrastructure setup tree
====================================

The tree with infra-setup dir as root contains a set of
ansible playbook and roles whose goal is to teardown and
provision/setup all the servers needed to aid in the test
and promotion of TripleO.

TripleO CI infrastruture
========================

This set of ansible playbooks creates these servers, using a
common structure for each one

tripleo-infra tenant

  * DNS
  * promoter
  * logs
  * jumphost
  * sova

openstack-nodepool tenant

  * te-broker


Roles and Playbook design
-------------------------

The creation process is split into two distinct phases: the
provisioning and the setup

The Provisioning
++++++++++++++++

this part is run directly by a user, it uses user's
credentials to interact directly with rdocloud and provision
all the networks, security and servers.

A users should:

* source OS credentials
* (optional) create ansible virtualenv
* install packages: ansible, shade

* run the command ansible-playbook -vvvv -i inventories/inventory.ini full_run.yml

The playbook will extract the informations on which tenant
to consider for the provisioning from the OS credentials
sources, and will automatically all the configuration
variables from the correct tenant_vars subtree

The teardown
++++++++++++

Tearing down the existing infrastructure element is part of
provisioning process. It's extremely conservative and it's
completely disabled unless the user explicitly specifies to
include the roles that teardown the servers and/or all the
other elements. Specifying to include the roles is still not
enough, elements to be tear down need to be explicitly
specified.
For example, if a user wants to include the server teardown
role, but delete only the dns server it must pass these two
options:

servers_teardown:
    include_role: true
    include_servers:
       - dns

the include__<element> option accept the wildcard "*"
(quoted) which specifies we want to delete all the member of
the specified group. Some element behaves differently
because there is no ansible module available to gather all
the elements, so the "*" wildcard actually deletes only the
server that are present in the local tree tenant configuration.
in the subtree tests/ the file nuke.yaml contains an example
of how to teardown every element on the infrastructure
tenant.

The setup
+++++++++

The playbook server__setup takes care of the setup part. It
calls a base setup role common to all the servers, then
calls the specific server role, based on the server
hostname.
But there's an important thing to understand.
When the provisioning part ends, also does the user direct
interaction. Each server is configured to pull down and apply
its configuration on its own, using cloud-init configuration
to bootstrap this process.

So there is not direct setup part in the main playbook,
after a server is created, it configures itself
automatically.
This is a crucial point, it means that the roles that are
later applied to the server are not launched with the same
set of variables that are passed by the user. If a variable
is needed during the setup part, for example some
credentials that must remain secret, it must be passed
indirectly through cloud-init configuration in the provision
step.
For example, the te-broker adopts a cloud-init configuration
that writes a file with content taken from the user
environment variables

    # cloud-config
    - write__files:
       content: |


The runcmd part is used to bootstrap the first playbook run,
which applies servers_setup playbook.
As stated, the playbook will apply basic and specific
configuration, including a task to call a similar
ansible-pull command periodically with cron.
The server will effectively update its configuration every
time there's a change in base or specific role.

Workflow Configuration
----------------------

Let's see now how to configure the process.
The provisioner machine, which is currently the user
machine, accepts and uses config variables (for example the
teardown configuration)
As stated, the provisioner will then include all the
variables in the tenant_vars/<tenant> subtree based on the
OS_TENANT_NAME environment variable exported from the
OS credentials sourced.
The tenant_vars subtree divides the configuration into two
main tenants: openstack-nodepool and tripleo-infra.
Variables that should be accessible from both tenant
configuration should be put into the file
tenant_vars/common.yml
Each <tenant> subtree contains four configuration files:

 * common.yml: for variables common to all the other
   sections, valid within the same tenant only
 * networks.yml: contains the configuration to provision
   networks, subnets, and routers.
 * security.yml: contains the configuration for the security
   groups, and eventually for additional keypairs, if need
   arises.
 * servers.yml: contains the configuration for all the
   servers in a specific tenant. Each server will specify its
   own volumes, ports, floating ips and so on.

It's important to notice that all the roles involved in
provisioning are pure generic roles, there is no hardcoded
configuration. All the ansible openstack cloud modules are
used with their respective variables included, but defaulted
to be omitted if they are not specified. All the variables
passed to these modules are taken from the configuration,
with their respective names.
For example to crate a server it's possible to include this
configuration in the tenant_vars/<tenant>/server.yml

servers:
   - name: example-server
     flavor: m1.tiny
     image: CentOS-7
     nics:
       - network-name: private
     volumes:
       - display_name: example-volume
         size: 100G

the variables name, flavor, image, nics are passed directly
to the os_server ansible module, and they maintain the same
name as this module use. so flavor is passed as flavor to
os_server.
The volumes: and ports: parts are treated differently, the
list contained in these variables are passed directly to the
os_volumes and os_ports modules instead, but the method is
the same, display_name will be passed to the os_volumes
display_name argument.
Security rules follow a similar pattern.

The userdata variable in each configuration contains the
important cloud-init configuration used to bootstrap the
server, and to also pass all the environment variables that
will be needed by the server for the bootstrap process.
The base role will also include tenant_vars/common.yml file,
to avail of any variable common to all the tenants.
