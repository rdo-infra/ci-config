#!/bin/bash

# Not sure why, but podman disconects after a while, need authenticate again
# Check if we are logged

podman login --get-login quay.io
if [ "$?" -gt "0" ]; then
    podman login quay.io --username $USERNAME --password $PASSWORD
fi

# Master
copy-quay --token $TOKEN --from-namespace tripleomaster \
                    --to-namespace tripleomaster tag --api-release master &>>/root/logs/tag/master.txt

# Victoria
copy-quay --token $TOKEN --from-namespace tripleovictoria \
                    --to-namespace tripleovictoria tag --api-release victoria &>>/root/logs/tag/victoria.txt

# Ussuri
copy-quay --token $TOKEN --from-namespace tripleoussuri \
                    --to-namespace tripleoussuri tag --api-release ussuri &>>/root/logs/tag/ussuri.txt
# Train 7
copy-quay --token $TOKEN --from-namespace tripleotrain \
                    --to-namespace tripleotrain tag --api-release train &>>/root/logs/tag/train.txt

# Train 8
copy-quay --token $TOKEN --from-namespace tripleotraincentos8 \
                    --to-namespace tripleotraincentos8 tag --api-release train8 &>>/root/logs/tag/train8.txt

# Stein
copy-quay --token $TOKEN --from-namespace tripleostein \
                    --to-namespace tripleostein tag --api-release stein  &>>/root/logs/tag/stein.txt

# Rocky
copy-quay --token $TOKEN --from-namespace tripleorocky \
                    --to-namespace tripleorocky tag --api-release &>>/root/logs/tag/rocky.txt
