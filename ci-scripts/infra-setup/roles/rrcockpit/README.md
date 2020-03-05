## tripleo-ci ruck|rover cockpit:

This is where the code behind
[http://cockpit-ci.tripleo.org/](http://cockpit-ci.tripleo.org/) lives. This
README will help you setup a development environment for the tripleo-ci
ruck|rover cockpit.

### Note for Fedora 31:

The Docker package has been removed from Fedora 31. It has been replaced by the upstream
package moby-engine, which includes the Docker CLI as well as the Docker Engine. However, we
recommend instead that you use Package-x-generic-16.pngpodman, which is a Cgroups v2-
compatible container engine whose CLI is compatible with Docker's. Fedora 31 uses Cgroups v2 by
default.
The moby-engine package does not support Cgroups v2 yet, so if you need to run the moby-engine
or run the Docker CE package, then you need to switch the system to using Cgroups v1, by passing
the kernel parameter
To do this permanently,
run sudo grubby --update-kernel=ALL --args="systemd.unified_cgroup_hierarchy=0"
This command reverts the systemd configuration to use cgroup v1.
Or if you have a vm running fedora 30 with docker installed use the export DOCKER_HOST
export DOCKER_HOST = "tcp://system-IP:custom-port"

### Note: Using an OpenStack VM (eg RDO Cloud) for development

It is possible to use a vm for development purposes. Follow the usual installation
instructions below and then see the section
[Accessing the cockpit on a remote host](https://github.com/rdo-infra/ci-config/blob/master/ci-scripts/infra-setup/roles/rrcockpit/README.md#accessing-the-cockpit-on-a-remote-host)

### Requirements:

The cockpit uses docker containers to run the required services - telegraf,
grafana, influxdb and mariadb.
To install
i. [docker](https://docs.docker.com/install/)
ii. [docker compose](https://docs.docker.com/compose/install/)
Make sure the user is also added to the [docker group](https://docs.docker.com/install/linux/linux-postinstall/)
and start the docker service to avoid the following
permissions error:
```
+ docker volume create telegraf-volume
Got permission denied while trying to connect to the Docker daemon socket at
unix:///var/run/docker.sock: Post http://%2Fvar%2Frun%2Fdocker.sock
```
### Starting the cockpit

There is a simiple script included in this repo that will help start up the
required service container with docker-compose - see
[development_script.sh](https://github.com/rdo-infra/ci-config/blob/master/ci-scripts/infra-setup/roles/rrcockpit/files/development_script.sh). Running with -s will start up the
cockpit:

```
[m@192 files]$ ./development_script.sh -s
+ '[' -z -s ']'
+ '[' -s '!=' '' ']'
+ case $1 in
+ shift
+ start
+ docker volume create telegraf-volume
telegraf-volume
+ docker volume create grafana-volume
grafana-volume
+ docker volume create influxdb-volume
influxdb-volume
+ docker volume create mariadb-volume
mariadb-volume
+ docker-compose up
Starting nginx    ... done
Starting mariadb  ... done
Starting influxdb        ... done
Starting mariadb-sidecar ... done
Starting telegraf        ... done
Starting grafana         ... done
Starting grafana-sidecar ... done
Attaching to nginx, mariadb, influxdb, mariadb-sidecar, telegraf, grafana, grafana-sidecar
```

Note it may take a while to load especially on first run. You will see that the
containers are being pulled before starting them like:

```
Pulling mariadb (mariadb:10.4.2-bionic)...
Trying to pull repository docker.io/library/mariadb ...
sha256:0a6456f1c6cc818f55a2d12a03f85429165235c6676943e2f12e6b36bb67892e: Pulling from docker.io/library/mariadb
Pulling nginx (nginx:latest)...
Trying to pull repository docker.io/library/nginx ...
sha256:eb3320e2f9ca409b7c0aa71aea3cf7ce7d018f03a372564dbdb023646958770b: Pulling from docker.io/library/nginx
f5d23c7fed46: Downloading [====>                                              ] 2.514 MB/27.09 MB
```
Once services start successfully you will begin to see the influxdb queries:

```
influxdb           | [httpd] 172.18.0.5 - - [26/Jul/2019:13:19:30 +0000] "GET /query?db=telegraf&epoch=s&q=SELECT+max%28%22cpu_time_user%22%29+FROM+%22procstat%22+WHERE+%28%22host%22+%3D+%27promoter%27+AND+%22pattern%22+%3D+%27%5Epython.%2Adlrnapi_promoter.py+.%2AFedora-28.%2Amaster.%2A%27%29+AND+time+%3E+now%28%29+-+6h+GROUP+BY+time%281m%29+fill%280%29 HTTP/1.1" 200 57 "-" "Grafana" 0066f579-afa8-11e9-83b7-0242ac120002 1632
```

This is important as it also gives you the local address that is serving the
cockpit on port 3000. So in the case above, you can use http://172.18.0.5:3000
or http://localhost:8080
in a browser to see the cockpit.

Once you load the page you will have to find "Cockpit" by clicking on Home in
the top-left of the loaded page. Note that it will take a while before the
various fields of the cockpit are populated.

### Accessing the cockpit on a remote host

If you are using a VM or other remote host for developing the cockpit you will
some extra steps to access it from a remote host (like from your local work
machine for example).

The following assumes a centos 7 vm running in an OpenStack cloud (RDO cloud)
with a floating IP attached.

First ensure that the security group that your vm belongs to allows ingress
access. Choose a port that you want to use for accessing grafana remotely and
allow ingress access to it by adding a rule in the relevant security group.

We will use remote SSH tunnelling to allow remote access to the cockpit. Before
setting up the tunnel you must ensure your sshd config allows it by enabling
GatewayPorts:

```
sudo vim /etc/ssh/sshd_config
GatewayPorts yes
sudo systemctl restart sshd
```
Then you can setup the SSH tunnel pointing to the local address and port
serving the ruck|rover cockpit. Assuming:

  * Cockpit running at 172.18.0.6:3000
  * VM floating IP is 41.125.31.115
  * You will use port 5000 to reach the cockpit (and this is allowed in the
    relevant security group).
  * You will use http://41.125.31.115:5000 to reach the cockpit

The tunnel is created with:
```
ssh -R 5000:172.18.0.6:3000 41.125.31.115
```

### Developing the ruck|rover cockpit

You can edit the cockpit directly in the browser but you first need to login
using the link in the bottom left corner. The default user/pass are
"admin"/"admin".

Once you've made any changes you need to click 'save' in the cockpit. However
to submit any changes as reviews upstream you first need to export those
changes into the cockpit.dashboard.json file. You may notice that after you
have made and saved changes, but before exporting them, git will show there
have been no changes made to the cockpit.dashboard.json.

Luckily there are scripts included for export and import of the json data. The
scripts are in the [files/grafana directory](https://github.com/rdo-infra/ci-config/tree/master/ci-scripts/infra-setup/roles/rrcockpit/files/grafana).

#### create-api-key.py

First create the required key using [create-api-key.py](https://github.com/rdo-infra/ci-config/blob/master/ci-scripts/infra-setup/roles/rrcockpit/files/grafana/create-api-key.py).

```
./create-api-key.py --key-name foo > grafana.key
```

#### export-grafana.py and import-grafana.py

The two scripts export-grafana.py and import-grafana.py are used to export the
cockpit data to json and then import the data back into the local cockpit,
respectively. For both you will need to pass the local address that the
cockpit is being served on using the --host parameter.

```
./export-grafana.py --host http://172.18.0.6:3000
./import-grafana.py --host http://172.18.0.6:3000
```

#### Create a snapshot

After you've saved and exported your changes into a code review you should
also create a shareable snapshot. You can do this via the 'share' button along
the top bar, and selecting the Snapshot tab. You can then include a link to
this together with your code submission.

## Stopping the ruck|rover cockpit

The service containers and services can be stopped with a ctrl-c in the main
server window. You will see it try to gracefully shut-down all the things:

```
^[[6~telegraf           | 2019-07-26T13:25:40Z D! Output [influxdb] buffer fullness: 0 / 10000 metrics.
^CGracefully stopping... (press Ctrl+C again to force)
Stopping grafana-sidecar ...
Stopping telegraf        ... done
Stopping grafana         ...
Stopping mariadb-sidecar ...
Stopping nginx           ... done
Stopping influxdb        ...
Stopping mariadb         ...

```

If you want to clear all local data you can use the development_script.sh with
the -c (--clean).

## Testing and changing telegraf scripts

First install the requirements
```
> pip install --user -r files/telegraf/requirements.txt
```
Then you can do a telegraf test on them for example for launchpad
```
> cd files/telegraf
> PATH=.:$PATH telegraf --test --config telegraf.d/launchpad.conf
```
The scripts are very standalone so you can directly execute them
```
> cd files/telegraf
> ./launchpad_bugs.py --tag promotion-blocker
```
If you see errors with "telegraf --test" like
'Error in plugin [inputs.exec]: metric parse error: expected field at offset 497'
It means that there is stuff generatd by the python script at character 497
that telegraf cannot parse

Best way to fix those is dumping with the python script with the options from
telegraf to a file and doing with "vim" a ":goto 497" to go to the character
from this you can iterate until "telegraf --test" passes.

## InfluxDB performance

InfluxDB can have problems with memory consumption. To prevent this it's better
to use [TSI indexes](https://docs.influxdata.com/influxdb/v1.7/concepts/tsi-details/).
If you don't use it right now, it's possible to
[convert existing data](https://docs.influxdata.com/influxdb/v1.7/tools/influx_inspect/#buildtsi)
to use it, see these [guidelines](https://www.influxdata.com/blog/how-to-overcome-memory-usage-challenges-with-the-time-series-index/).
Enabled this for TripleoCI dashboard with https://review.rdoproject.org/r/#/c/25261
