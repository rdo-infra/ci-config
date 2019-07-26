## tripleo-ci ruck|rover cockpit:

This is where the code behind
[http://cockpit-ci.tripleo.org/](http://cockpit-ci.tripleo.org/) lives. This
README will help you setup a development environment for the tripleo-ci
ruck|rover cockpit.

### Requirements:

The cockpit uses docker containers to run the required services - telegraf,
grafana, influxdb and mariadb. So docker must be installed and running on
the development box before proceeding. Make sure the user is also added to
the docker group to avoid the following permissions error:

```
+ docker volume create telegraf-volume
Got permission denied while trying to connect to the Docker daemon socket at unix:///var/run/docker.sock: Post http://%2Fvar%2Frun%2Fdocker.sock
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

Once services start successfully you will begin to see the influxdb queries:

```
influxdb           | [httpd] 172.18.0.5 - - [26/Jul/2019:13:19:30 +0000] "GET /query?db=telegraf&epoch=s&q=SELECT+max%28%22cpu_time_user%22%29+FROM+%22procstat%22+WHERE+%28%22host%22+%3D+%27promoter%27+AND+%22pattern%22+%3D+%27%5Epython.%2Adlrnapi_promoter.py+.%2AFedora-28.%2Amaster.%2A%27%29+AND+time+%3E+now%28%29+-+6h+GROUP+BY+time%281m%29+fill%280%29 HTTP/1.1" 200 57 "-" "Grafana" 0066f579-afa8-11e9-83b7-0242ac120002 1632
```

This is important as it also gives you the local address that is serving the
cockpit on port 3000. So in the case above, you can use http://172.18.0.5:3000
in a browser to see the cockpit.

Once you load the page you will have to find "Cockpit" by clicking on Home in
the top-left of the loaded page. Even then however you'll find that there is
no data being shown. For that you'll have to initialise the data with the steps
in the next section.

### Initialise cockpit data

Luckily there are scripts included for this too, in the
[files/grafana](https://github.com/rdo-infra/ci-config/tree/master/ci-scripts/infra-setup/roles/rrcockpit/files/grafana) directory.

First create the required key using [create-api-key.py](https://github.com/rdo-infra/ci-config/blob/master/ci-scripts/infra-setup/roles/rrcockpit/files/grafana/create-api-key.py).

```
./create-api-key.py --key-name foo > grafana.key
```

The two scripts export-grafana.py and import-grafana.py are used to export the
cockpit data to json and then import the data back into the local cockpit,
respectively. For both you will need to pass the local address that the
cockpit is being served on using the --host parameter.

```
./export-grafana.py --host http://172.18.0.6:3000
./import-grafana.py --host http://172.18.0.6:3000
```

Finally restart the local cockpit - stop it with ctrl-c and you should see it
try to gracefully shut-down all the things:

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

Finally use development_script.sh -s to start the service again. Note the IP
address may change so watch for the influxdb messages to find the right
adddress to open in the browser.

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
