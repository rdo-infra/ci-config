#!/bin/bash

# Not sure why, but podman disconects after a while, need authenticate again
# Check if we are logged

podman login --get-login quay.io
if [ "$?" -gt "0" ]; then
    podman login quay.io --username $USERNAME --password $PASSWORD
fi

# Master
/usr/local/bin/copy-quay --config /root/copy-quay/config.yaml --token $TOKEN --release master --html /root/logs/master-report.html copy &>>/root/logs/master.txt

# Master centos 9
/usr/local/bin/copy-quay --config /root/copy-quay/config.yaml --token $TOKEN --release mastercentos9 --html /root/logs/master-centos9-report.html copy &>>/root/logs/mastercentos9.txt

# Wallaby
/usr/local/bin/copy-quay --config /root/copy-quay/config.yaml --token $TOKEN --release wallaby --html /root/logs/wallaby-report.html copy &>>/root/logs/wallaby.txt

# Wallaby centos 9
/usr/local/bin/copy-quay --config /root/copy-quay/config.yaml --token $TOKEN --release wallabycentos9 --html /root/logs/wallaby-centos9-report.html copy &>>/root/logs/wallabycentos9.txt

# Victoria
/usr/local/bin/copy-quay --config /root/copy-quay/config.yaml --token $TOKEN --release victoria --html /root/logs/victoria-report.html copy &>>/root/logs/victoria.txt

# Ussuri
/usr/local/bin/copy-quay --config /root/copy-quay/config.yaml --token $TOKEN --release ussuri --html /root/logs/ussuri-report.html copy &>>/root/logs/ussuri.txt

# Train 7
/usr/local/bin/copy-quay --config /root/copy-quay/config.yaml --token $TOKEN --release train7 --html /root/logs/train-report.html copy &>>/root/logs/train.txt

# Train 8
/usr/local/bin/copy-quay --config /root/copy-quay/config.yaml --token $TOKEN --release train8 --html /root/logs/train8-report.html copy &>>/root/logs/train8.txt
