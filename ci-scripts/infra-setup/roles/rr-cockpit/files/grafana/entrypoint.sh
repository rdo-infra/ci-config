#!/bin/bash -e

admin_user=admin
admin_password=admin
data_dir=/var/lib/grafana/
api_key_name="grafana-sidecar"
api_key_path=$data_dir/$api_key_name.api.key
host=grafana:3000
api_url=http://$admin_user:$admin_password@grafana:3000

if [ ! -f $api_key_path ]; then
    if ! ./create-api-key.py --url $api_url --key-name ${api_key_name} > $api_key_path; then
        rm $api_key_path
    fi
fi

# Wait a little for grafana to startup
sleep 3

./import-grafana.py --host http://$host --key $(cat $api_key_path)

./grafana-alert-notification-server.py \
                        --grafana-host $api_url \
                        --grafana-key $(cat $api_key_path)
