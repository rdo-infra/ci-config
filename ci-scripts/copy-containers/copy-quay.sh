#!/bin/bash

# Not sure why, but podman disconects after a while, need authenticate again
# Check if we are logged

podman login --get-login quay.io
if [ "$?" -gt "0" ]; then
    podman login quay.io --username $USERNAME --password $PASSWORD
fi

# Master
/usr/local/bin/copy-quay --token $TOKEN --from-namespace tripleomaster \
                    --to-namespace tripleomaster copy &>>/root/logs/master.txt

# Wallaby
/usr/local/bin/copy-quay --token $TOKEN --from-namespace tripleowallaby \
                    --to-namespace tripleowallaby --job periodic-tripleo-ci-build-containers-ubi-8-push-wallaby \
                    --html /root/logs/wallaby-report.html copy &>>/root/logs/wallaby.txt
# Victoria
/usr/local/bin/copy-quay --token $TOKEN --from-namespace tripleovictoria \
                    --to-namespace tripleovictoria --job periodic-tripleo-ci-build-containers-ubi-8-push-victoria \
                    --html /root/logs/victoria-report.html copy &>>/root/logs/victoria.txt

# Ussuri
/usr/local/bin/copy-quay --token $TOKEN --from-namespace tripleoussuri \
                    --to-namespace tripleoussuri --job periodic-tripleo-ci-build-containers-ubi-8-push-ussuri \
                    --html /root/logs/ussuri-report.html copy &>>/root/logs/ussuri.txt
# Train 7
/usr/local/bin/copy-quay --token $TOKEN --from-namespace tripleotrain \
                    --to-namespace tripleotrain --job periodic-tripleo-centos-7-train-containers-build-push \
                    --html /root/logs/train-report.html copy &>>/root/logs/train.txt

# Train 8
/usr/local/bin/copy-quay --token $TOKEN --from-namespace tripleotraincentos8 \
                    --to-namespace tripleotraincentos8 --job periodic-tripleo-ci-build-containers-ubi-8-push-train \
                    --html /root/logs/train8-report.html copy &>>/root/logs/train8.txt

# Stein
/usr/local/bin/copy-quay --token $TOKEN --from-namespace tripleostein \
                    --to-namespace tripleostein --job periodic-tripleo-centos-7-stein-containers-build-push \
                    --html /root/logs/stein-report.html copy &>>/root/logs/stein.txt
