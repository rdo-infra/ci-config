# Guidelines for using Molecule

## Naming convention

Having a naming convention should help us ease maintenance, lower confusions
and set expectations without having to read descriptions or source code.

### Job names

We should aim to keep scenario and job names short and concise, minimizing the
change that we would need to read full description or their source in order
to figure-out what they are doing.

All molecule jobs must have a description, one that includes enough information
about what it does but without repeating obvious facts from its name.

New molecule jobs should follow the naming convention listed below:

`mol-scenario_name` or when **more than one platform is supported**, to add it
as a suffix, like `mol-scenario_name-centos-8`.

Historically we used `delegated` tag to mark jobs that are using delegated
driver to make it easier to distinguish from the other ones which used a
managed virtualized driver like docker or podman. We should no longer include
driver name in job name because that is just an implementation detail, and
we may decide to swap drivers based on our needs. Changing job names does
prevent us from tracking their execution history.

Notes:

* `mol-` prefix is shorter than current `molecule-` one and allows us to
  distinguish between new generation of jobs and old ones. Next version
  of molecule will include a `mol` command alias.
* While we still use tox to run molecule jobs, we no longer want to expose that
  in job names, as being an implementation detail. The expectation is that the
  developer can run the same test directly with molecule. This approach will
  allow us to bypass using tox in the future without having to change our jobs.
* very long job names affect web interface display in zuul/gerrit/dashboard,
  generate urls that do not fit well in browser/email/irc due extra wrapping or
  limited space.

## Molecule scenarios

Starting with July 2020, we aim to promote keeping all test scenarios, from
all roles, inside repository root `/molecule`.  Historically molecule folders
were hosted inside each role folder but this causes some problems:

* some tests are aimed towards playbooks and not individual roles
* difficult code reuse from other roles, renaming/moving roles even harder
* hard to know from which subdirectory to run molecule cli from
* `default` scenario could become bit confusing

This newer flat layout helps with favour aspects:

* better suited for adoption of official Ansible collection layout
* all scenarios, from all roles, are in one place
* developer can always call any scenario from the repository root

To avoid confusions, we no longer recommend defining a `default` scenario for
any multi-role repository as its purpose would be confusing.

Scenario name should match role name being tested, as this makes it much
easier to setup job trigger patterns like `.*/my_role.*`, which will cover
not only the role body itself, but also the scenario. Note that there is no
slash after the role name, as we may need to add more than one scenario
per-role.

* Split tasks between: `prepare`, `converge` and `verify` playbooks based on
  their purpose.
* `prepare` is supposed to bring the host to the expected state before running
  test, mainly installing prerequisites, mainly doing some cleanups. In scope,
  it can be seen as mocking phase
* `converge` must be keep as small as possible, replicating how the tested
  code is expected to be used in production, without mocking and special
  cases inside it.
* `verify` is more like post in zuul, we assert that converge did whatever it
  was expected to do. When tested playbook/role has internal verifications,
  this can be skipped. Still, is good to have something that validates the
  final outcome.
* Do not ever put `task` files inside a folder that already has `playbooks`.
  If you need tasks, use a `tasks/` folder to host them.
* Avoid doing relative task includes from other roles, especially if these
  roles are located in another location than `roles/` from repository root.

### Delegated scenarios

When writing delegated scenarios, **always assume that you cannot sudo on
localhost**.  You do not want to accidentally reconfigure a developer
machine when he forgot to secure sudo with a password.

On Zuul CI/CD, only by chance it happens that we allow sudo for molecule jobs,
but you should always refer to the `instance` or `tester` host. Our jobs
will assure than on CI, Ansible will be able to `ssh root@instance` without
any problems.

This means that for local testing, you only need to create a spare host and
add something like:

```bash
# ~/.ssh/config
Host instance tester
  HostName 1.2.3.4  # <-- can be anywhere, Zuul and YOLO people use 127.0.0.1
  User root
```

### Sharing code between scenarios

We do not have a full set of guidelines for sharing code, so for the moment
keep using current practices, until we decide which approach is better.

Obviously that if we have a set of tasks that is common between multiple
testing playbooks, we should reuse them, symlinks or includes are ok but you
may also consider creating internal roles.

## Calling molecule

If you just want to see which scenarios are available run:

```bash
source .tox/molecule/bin/activate  # only if you do not have molecule installed locally
molecule list
```

Assuming that we have a job named `mol-foo`, you should run the same test
locally using either:

```bash
molecule test -s foo
```

## Ansible Guidelines

* Try to gradually rename all roles to avoid use of `-`, using `_` instead.
  This step is required by collection layout.
* Move all roles to `roles/` folder, no more nesting.
* Be sure you read [Developing Collections](https://docs.ansible.com/ansible/latest/dev_guide/developing_collections.html) -- even if we do not build and publish our code
  as a collection today, there is no reason not to migrate towards the
  recommended layout. Keep in mind that not every page on Ansible or Molecule
  docs was updated to follow these recomandations. When in doubt ask others,
  or use `#ansible-molecule` and `#ansible-devel` channels.
* Presence of `library` folder on repository root is now deprecated, please
  use `plugins/modules` instead, as officially recommended for collections.

### Modules, plugins and filters

Prior to collections (2.9+), there was no official way to install
Ansible extensions. Modules were supposed to be included inside roles and
visible only to the role that had them.

Only collections allow you to install bundles of playbooks, roles, modules,
filters and plugins. Still, until our minimum supported version of Ansible
becomes 2.9, we cannot rely on them and we have to manually install these.

It is in our interest to keep these Ansible components in the recommended
locations.

When Ansible runs under Zuul, we can include **roles and modules** but **not
filters or plugins**. This is due to security measures as these run on Ansible
controller and they would have access to all Zuul managed secrets. Keep this
in mind when deciding on how to implement more complex functions.

We [learned this the hard way](https://review.opendev.org/#/c/717723/) when
working on log collection and we had to rewrite a Jinja filter as an Ansible
module in order to make it work under Zuul too.

When writing a module be sure you also include a generic role that just
calls this new module. This allows us to consume the module from older
versions of Ansible, including directly from Zuul.
