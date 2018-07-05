#!/bin/bash -e

admin_user=admin
admin_password=admin
data_dir=/var/lib/grafana/
api_key_name="grafana-sidecar"
api_key_path=$data_dir/$api_key_name.api.key
api_url=http://$admin_user:$admin_password@grafana:3000

ls -la $data_dir

rm $api_key_path

if [ ! -f $api_key_path ]; then
    ./create-api-key.py --url $api_url --key-name ${api_key_name} > $api_key_path
fi

./grafana-alert-notification-server.py \
                        --grafana-host $api_url \
                        --grafana-key $(cat $api_key_path)
