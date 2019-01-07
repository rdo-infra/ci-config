Development Setup Instructions.

This will setup the most basic development environment. To make changes save changes locally,
and docker rm and rmi the "files_" container and images, then run docker-compose up again.

> cd files
> docker volume create influxdb-volume
> docker volume create grafana-volume
> docker volume create telegraf-volume
> docker-compose up

Exporting/Importing local grafana changes

> cd files/grafana

Generate the API key 'grafana.key' if nis not already present

> ./create-api-key --key-name "foo" > grafana.key

Dump grafana UI to json files

> ./export-grafana.py

Dump json files to grafana UI

> ./import-grafana.py
