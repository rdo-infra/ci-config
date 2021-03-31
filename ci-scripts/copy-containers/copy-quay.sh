#!/bin/bash

# Not sure why, but podman disconects after a while, need authenticate again
# Check if we are logged

podman login --get-login quay.io
if [ "$?" -gt "0" ]; then
    podman login quay.io --username $USERNAME --password $PASSWORD
fi

# Master
copy-quay --token $TOKEN --from-namespace tripleomaster \
                    --to-namespace tripleomaster copy &>>/root/logs/master.txt

# Victoria
copy-quay --token $TOKEN --from-namespace tripleovictoria \
                    --to-namespace tripleovictoria --job periodic-tripleo-ci-build-containers-ubi-8-push-victoria copy &>>/root/logs/victoria.txt

# Ussuri
copy-quay --token $TOKEN --from-namespace tripleoussuri \
                    --to-namespace tripleoussuri --job periodic-tripleo-ci-build-containers-ubi-8-push-ussuri copy &>>/root/logs/ussuri.txt
# Train 7
copy-quay --token $TOKEN --from-namespace tripleotrain \
                    --to-namespace tripleotrain --job periodic-tripleo-centos-7-train-containers-build-push copy &>>/root/logs/train.txt

# Train 8
copy-quay --token $TOKEN --from-namespace tripleotraincentos8 \
                    --to-namespace tripleotraincentos8 --job periodic-tripleo-ci-build-containers-ubi-8-push-train copy &>>/root/logs/train8.txt

# Stein
copy-quay --token $TOKEN --from-namespace tripleostein \
                    --to-namespace tripleostein --job periodic-tripleo-centos-7-stein-containers-build-push copy &>>/root/logs/stein.txt

# Rocky
copy-quay --token $TOKEN --from-namespace tripleorocky \
                    --to-namespace tripleorocky --job periodic-tripleo-centos-7-rocky-containers-build-push copy &>>/root/logs/rocky.txt
