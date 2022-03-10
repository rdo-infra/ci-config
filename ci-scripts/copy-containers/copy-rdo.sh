#!/bin/bash

# Check if podman is logged
podman login --get-login trunk.registry.rdoproject.org
if [ "$?" -gt "0" ]; then
    podman login trunk.registry.rdoproject.org --username $RDO_USERNAME --password $RDO_PASSWORD
fi

#  Master centos 8
HASH=`curl 'https://trunk.rdoproject.org/api-centos8-master-uc/api/promotions?promote_name=current-tripleo&limit=1' 2>/dev/null | jq -r '.[0].aggregate_hash'`
/usr/local/bin/copy-quay --config /root/copy-quay/config.yaml --pull-registry quay.io --push-registry trunk.registry.rdoproject.org --token $TOKEN --push-hash $HASH --hash $HASH --release master copy

# Master centos 9
HASH=`curl 'https://trunk.rdoproject.org/api-centos9-master-uc/api/promotions?promote_name=current-tripleo&limit=1' 2>/dev/null | jq -r '.[0].aggregate_hash'`
/usr/local/bin/copy-quay --config /root/copy-quay/config.yaml --pull-registry quay.io --push-registry trunk.registry.rdoproject.org --token $TOKEN --push-hash $HASH --hash $HASH --release mastercentos9 copy

# Wallaby centos 8
HASH=`curl 'https://trunk.rdoproject.org/api-centos8-wallaby/api/promotions?promote_name=current-tripleo&limit=1' 2>/dev/null | jq -r '.[0].aggregate_hash'`
/usr/local/bin/copy-quay --config /root/copy-quay/config.yaml --pull-registry quay.io --push-registry trunk.registry.rdoproject.org --token $TOKEN --push-hash $HASH --hash $HASH --release wallaby copy

# Wallaby centos 9
HASH=`curl 'https://trunk.rdoproject.org/api-centos9-wallaby/api/promotions?promote_name=current-tripleo&limit=1' 2>/dev/null | jq -r '.[0].aggregate_hash'`
/usr/local/bin/copy-quay --config /root/copy-quay/config.yaml --pull-registry quay.io --push-registry trunk.registry.rdoproject.org --token $TOKEN --push-hash $HASH --hash $HASH --release wallabycentos9 copy

# Victoria
HASH=`curl 'https://trunk.rdoproject.org/api-centos8-victoria/api/promotions?promote_name=current-tripleo&limit=1' 2>/dev/null | jq -r '.[0].aggregate_hash'`
/usr/local/bin/copy-quay --config /root/copy-quay/config.yaml --pull-registry quay.io --push-registry trunk.registry.rdoproject.org --token $TOKEN --push-hash $HASH --hash $HASH --release victoria copy

# Ussuri
HASH=`curl 'https://trunk.rdoproject.org/api-centos8-ussuri/api/promotions?promote_name=current-tripleo&limit=1' 2>/dev/null | jq -r '.[0].aggregate_hash'`
/usr/local/bin/copy-quay --config /root/copy-quay/config.yaml --pull-registry quay.io --push-registry trunk.registry.rdoproject.org --token $TOKEN --push-hash $HASH --hash $HASH --release ussuri copy

# Train 8
HASH=`curl 'https://trunk.rdoproject.org/api-centos8-train/api/promotions?promote_name=current-tripleo&limit=1' 2>/dev/null | jq -r '.[0].aggregate_hash'`
/usr/local/bin/copy-quay --config /root/copy-quay/config.yaml --pull-registry quay.io --push-registry trunk.registry.rdoproject.org --token $TOKEN --push-hash $HASH --hash $HASH --release train8 copy
