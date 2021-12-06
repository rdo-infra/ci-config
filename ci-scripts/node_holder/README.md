As an engineer in CI team sometimes we need the ability to hold nodes
for debugging.

The current process is using cli commands from inside zuul-client
containers and passing ton of parameters like:-

a) Where the config file is present on host which we want to mount to
   zuul-client container?
b) Where we want to hold a node i.e in rdo/downstream?
c) reason
d) Job name
e) project name
f) change id
h) expiration time

~~~
podman run --rm --name zc_container \
-v /path/to/.config/zuul/:/config:Z zuul/zuul-client:latest \
-c /config/client.conf --use-config tripleo-ci-internal autohold \
--reason my_reason --job XXX --project ZZZ --change YYY \
--node-hold-expiration 86400
~~~

Apart from manual work, above steps have chances for human error.

This script automates the above work and also reduces the chances
of error, also this saves us from running zuul_container on our host.

Features of this script:-

A) Autodetect job name, project name, change id and config(patch belong to
   rdo/downstream/any other tenant config).
B) Use zuulclient python api instead of using cli commands.

Usage:-

Adding a node on hold:-
======================

If testproject/patch zuul layout contains single job:-

Need below paramaters:
* `--add_using_autodetect` or `-a` <Gerrit patch link to zuul layout file>
* `--reason <reason for the hold>` is optional but good to add.
* `-c` or `--confirm` to confirm that you want to add

Example:

Ran without `--confirm`
~~~
./node_holder.py -a https://review.rdoproject.org/r/c/testproject/+/28446/63/.zuul.yaml

Will add job: periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp-featureset001-master on
hold for project:testproject and change: 28446 in rdo
Please pass -c to confirm
~~~

Ran with `-c` or `--confirm`:-

~~~
./node_holder.py -a https://review.rdoproject.org/r/c/testproject/+/28446/63/.zuul.yaml -c

Adding job: periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp-featureset001-master on hold for
project: testproject and change: 28446 in rdo
~~~


If testproject/patch zuul layout contains more then 1 job, we will need one
additional parameter:-

* --job_name <job name>

Script will inform which all jobs are present in a zuul layout and
informs to pass --job_name <name of job> for job which you want to hold.
~~~
./node_holder.py -a https://review.rdoproject.org/r/c/testproject/+/36267/43/.zuul.yaml

Patch: https://review.rdoproject.org/r/c/testproject/+/36267/43/.zuul.yaml
contains more than 1 job, please pass --job_name <name of job> which job you want to hold

periodic-tripleo-centos-9-buildimage-overcloud-hardened-uefi-full-master
periodic-tripleo-centos-9-buildimage-overcloud-full-master
periodic-tripleo-centos-9-buildimage-ironic-python-agent-master
periodic-tripleo-ci-build-containers-centos-9-push-master
periodic-tripleo-ci-centos-9-ovb-3ctlr_1comp-featureset001-master
~~~

passed the --job_name param:-
~~~
./node_holder.py -a https://review.rdoproject.org/r/c/testproject/+/36267/43/.zuul.yaml
 --job_name periodic-tripleo-ci-build-containers-centos-9-push-master
 --reason ysandeep_debug -c

Adding job: periodic-tripleo-ci-build-containers-centos-9-push-master on hold for
project: testproject and change: 36267 in rdo
~~~



Listing jobs which are on hold:-
==============================


Need two paramaters:-
1)  `-l` / `--list`
2) `--config <rdo or downstream>`

~~~
./node_holder.py -l --config rdo

┏━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ID        ┃ Tenant ┃ Project                   ┃ Job                                                                ┃ ref_filter      ┃ Reason                ┃
┡━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━┩
│ 0000001145│ rdopr… │ review.rdoproject.org/te… │ periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp-featureset001-master  │ refs/changes/4… │ debug                 │
└───────────┴────────┴───────────────────────────┴────────────────────────────────────────────────────────────────────┴─────────────────┴───────────────────────┘
~~~

Deleting a node:
================

Option 1:  Deleting a node from using gerrit patch

Need below paramaters:-
* `d` or `--delete_using_autodetect` <Gerrit patch url>
* `-c` or `--confirm` to confirm that you want to delete

~~~
./node_holder.py -d https://review.rdoproject.org/r/c/testproject/+/28446/

Will remove periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp-featureset001-master
from hold for patch: 28446 Please pass -c to confirm
~~~


Option 2:  Deleting a node from using job id

Need below paramaters:-

* `--delete_with_id` <job id>
* `--config <rdo or downstream>`
* `-c` or `--confirm` to confirm that you want to delete

Ran without `--confirm`
~~~
./node_holder.py --delete_with_id 0000001145 --config rdo

Will remove periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp-featureset001-master from hold
Please pass -c to confirm
~~~

Ran with `-c` or `--confirm`:-
~~~
./node_holder.py --delete_with_id 0000001145 --config rdo -c

Removing periodic-tripleo-ci-centos-8-ovb-3ctlr_1comp-featureset001-master from hold
~~~
