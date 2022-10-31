#!/bin/bash

copy_quay() {
    HASH=$(curl "https://trunk.rdoproject.org/api-$1/api/promotions?promote_name=current-tripleo&limit=1" 2>/dev/null | jq -r '.[0].aggregate_hash')
    /usr/local/bin/copy-quay --config /root/copy-quay/config.yaml --pull-registry quay.io --push-registry quay.rdoproject.org --token "$TOKEN" --push-hash "$HASH" --hash "$HASH" --release "$2" copy
}
# Check if podman is logged
podman login --get-login quay.rdoproject.org
if [ "$?" -gt "0" ]; then
    podman login quay.rdoproject.org --username "$RDO_USERNAME" --password "$RDO_PASSWORD"
fi


# Master Centos 9
copy_quay centos9-master-uc mastercentos9

# Zed Centos 9
copy_quay centos9-zed zedcentos9

# Wallaby Centos 8
copy_quay centos8-wallaby wallaby

# Wallaby Centos 9
copy_quay centos9-wallaby wallabycentos9

# Train Centos 8
copy_quay centos8-train train8
