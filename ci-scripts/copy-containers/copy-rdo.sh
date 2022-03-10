#!/bin/bash

# Check if podman is logged
podman login --get-login trunk.registry.rdoproject.org
if [ "$?" -gt "0" ]; then
    podman login trunk.registry.rdoproject.org --username $RDO_USERNAME --password $RDO_PASSWORD
fi

# Wallaby centos 9
HASH=`curl 'https://trunk.rdoproject.org/api-centos9-wallaby/api/promotions?promote_name=current-tripleo&limit=1' 2>/dev/null | jq -r '.[0].aggregate_hash'`
/usr/local/bin/copy-quay --config /root/copy-quay/config.yaml --pull-registry quay.io --push-registry trunk.registry.rdoproject.org --token $TOKEN --push-hash $HASH --hash $HASH --release wallabycentos9 copy

# Master centos wallabycentos9
HASH=`curl 'https://trunk.rdoproject.org/api-centos9-master-uc/api/promotions?promote_name=current-tripleo&limit=1' 2>/dev/null | jq -r '.[0].aggregate_hash'`
/usr/local/bin/copy-quay --config /root/copy-quay/config.yaml --pull-registry quay.io --push-registry trunk.registry.rdoproject.org --token $TOKEN --push-hash $HASH --hash $HASH --release mastercentos9 copy
