#!/bin/bash

# Not sure why, but podman disconects after a while, need authenticate again
# Check if we are logged

podman login --get-login quay.io
if [ "$?" -gt "0" ]; then
    podman login quay.io --username $USERNAME --password $PASSWORD
fi

# Master
/usr/local/bin/copy-quay --token $TOKEN --from-namespace tripleomaster \
                    --to-namespace tripleomaster tag --release master \
                    --html /root/logs/tag/master-report.html &>>/root/logs/tag/master.txt

# Wallaby

/usr/local/bin/copy-quay --token $TOKEN --from-namespace tripleowallaby \
                    --to-namespace tripleowallaby tag --release wallaby \
                    --html /root/logs/tag/wallaby-report.html &>>/root/logs/tag/wallaby.txt
# Victoria
/usr/local/bin/copy-quay --token $TOKEN --from-namespace tripleovictoria \
                    --to-namespace tripleovictoria tag --release victoria \
                    --html /root/logs/tag/victoria-report.html &>>/root/logs/tag/victoria.txt

# Ussuri
/usr/local/bin/copy-quay --token $TOKEN --from-namespace tripleoussuri \
                    --to-namespace tripleoussuri tag --release ussuri \
                    --html /root/logs/tag/ussuri-report.html &>>/root/logs/tag/ussuri.txt
# Train 7
/usr/local/bin/copy-quay --token $TOKEN --from-namespace tripleotrain \
                    --to-namespace tripleotrain tag --release train \
                    --html /root/logs/tag/train-report.html &>>/root/logs/tag/train.txt

# Train 8
/usr/local/bin/copy-quay --token $TOKEN --from-namespace tripleotraincentos8 \
                    --to-namespace tripleotraincentos8 tag --release train8 \
                    --html /root/logs/tag/train8-report.html &>>/root/logs/tag/train8.txt

# Stein
/usr/local/bin/copy-quay --token $TOKEN --from-namespace tripleostein \
                    --to-namespace tripleostein tag --release stein \
                    --html /root/logs/tag/stein-report.html &>>/root/logs/tag/stein.txt

# Rocky
/usr/local/bin/copy-quay --token $TOKEN --from-namespace tripleorocky \
                    --to-namespace tripleorocky tag --release \
                    --html /root/logs/tag/rocky-report.html &>>/root/logs/tag/rocky.txt
