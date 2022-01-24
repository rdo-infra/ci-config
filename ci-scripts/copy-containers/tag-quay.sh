#!/bin/bash

# Not sure why, but podman disconects after a while, need authenticate again
# Check if we are logged

podman login --get-login quay.io
if [ "$?" -gt "0" ]; then
    podman login quay.io --username $USERNAME --password $PASSWORD
fi

# Master
/usr/local/bin/copy-quay --token $TOKEN --release master --html /root/logs/tag/master-report.html tag &>>/root/logs/tag/master.txt

# Master centos 9
/usr/local/bin/copy-quay --token $TOKEN --release mastercentos9 --html /root/logs/tag/master-centos9-report.html tag &>>/root/logs/tag/mastercentos9.txt

# Wallaby
/usr/local/bin/copy-quay --token $TOKEN --release wallaby --html /root/logs/tag/wallaby-report.html tag &>>/root/logs/tag/wallaby.txt

# Victoria
/usr/local/bin/copy-quay --token $TOKEN --release victoria --html /root/logs/tag/victoria-report.html tag &>>/root/logs/tag/victoria.txt

# Ussuri
/usr/local/bin/copy-quay --token $TOKEN --release ussuri --html /root/logs/tag/ussuri-report.html tag &>>/root/logs/tag/ussuri.txt

# Train 7
/usr/local/bin/copy-quay --token $TOKEN --release train7 --html /root/logs/tag/train-report.html tag &>>/root/logs/tag/train.txt

# Train 8
/usr/local/bin/copy-quay --token $TOKEN --release train8 --html /root/logs/tag/train8-report.html tag &>>/root/logs/tag/train8.txt

# Stein
/usr/local/bin/copy-quay --token $TOKEN --release stein --html /root/logs/tag/stein-report.html tag &>>/root/logs/tag/stein.txt
