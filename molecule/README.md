Guidelines for using Molecule
=============================

Naming convention
-----------------

Having a naming convention should help us ease maintenance, lower confusions
and set expectations without having to read descriptions or source code.

Job names
---------

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
  distinguish between new generation of jobs and old ones. Also next version
  of molecule will also have a `mol` command alias.
* While we still use tox to run molecule jobs, we no longer want to expose that
  in job names, as being an implementation detail. The expectation is that the
  develop can run the same test by just running molecule directly with scenario
  name. This approach will allow us to bypass using tox in the future without
  having to change our jobs.
* very long job names affect web interface display in zuul/gerrit/dashboard,
  generate urls that do not fit well in browser/email/irc due extra wrapping or
  limited space.

Molecule scenarios
------------------

Starting with June 2020, we aim to promote keeping all test scenarios inside
repository root `/molecule`.  Historically molecule folders where hosted inside
each role folder but this cases some problems:

* some tests are aimed towards playbooks and not individual roles
* difficult code reuse from other roles, renaming/moving roles even harder
* hard to know from which subdirectory to run molecule cli from
* `default` scenario could become bit confusing

This newer flat layout helps with favour aspects:

* better suited for adoption of official Ansible collection layout
* all scenarios are in one place
* developer can always call any scenario from the repository root

To avoid confusions, we no longer recommend defining a `default` scenario for
any multi-role repository as its purpose would be confusing.

Scenario name should match role name being tested, as this makes it much
easier to setup job trigger patterns like `.*/my_role.*`, which will cover
not only the role body itself, but also the scenario. Note that there is no
slash after the role name, as we may need to add more than one scenario
per-role.

Calling molecule
----------------

If you just want to see which scenarios are available run:

```base
molecule list
```

Assuming that we have a job named `mol-foo`, you should run the same test
locally using either:

```bash
molecule -s foo
tox -e molecule foo  # if you do not have molecule installed locally.
```
