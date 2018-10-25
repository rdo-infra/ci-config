Exporting/Importing local grafana changes

> cd files/grafana

Generate the API key 'grafana.key' if nis not already present

> ./create-api-key --key-name "foo" > grafana.key

Dump grafana UI to json files

> ./export-grafana.py

Dump json files to grafana UI

> ./import-grafana.py

