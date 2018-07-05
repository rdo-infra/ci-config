#!/bin/bash -e

admin_user=admin
admin_password=$GF_SECURITY_ADMIN_PASSWORD
data_dir=/var/lib/grafana/
api_key_name="grafana-sidecar"
api_key_path=$data_dir/$api_key_name.api.key
host=grafana:3000
api_url=http://$admin_user:$admin_password@$host

# Wait a little for grafana to startup
sleep 10

if [ ! -f $api_key_path ]; then
    if ! ./create-api-key.py --url $api_url --key-name ${api_key_name} > $api_key_path; then
        rm $api_key_path
    fi
fi


./import-grafana.py --host http://$host --key $api_key_path

./grafana-alert-notification-server.py \
                        --grafana-host http://$host \
                        --grafana-key $(cat $api_key_path)
