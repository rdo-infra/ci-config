#!/bin/bash
set -e

pip install demjson
# running a for loop in a stupid script is required as tox will not allow
# jsonlint -s dir/*.json :(
for i in `ls ci-scripts/infra-setup/roles/rrcockpit/files/grafana/*.json`;do
    jsonlint -s $i;
done
