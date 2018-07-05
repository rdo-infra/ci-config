#!/bin/bash

admin_user=admin
admin_password=admin
data_dir=/var/lib/grafana/
api_key_name="grafana-sidecar"
api_key_path=$data_dir/$api_key_name.api.key
api_url=http://$admin_user:$admin_password@grafana:3000/api/

if [ ! -f admin.key ]; then
    echo "Creating grafana api key $api_key_path"
    response=$(curl -X POST -H "Content-Type: application/json" -d '{"name":"$api_key_name", "role": "Admin"}' http://admin:admin@grafana:3000/api/auth/kys)

fi

echo ./grafana-alert-notification-server.py \
                        --grafana-host $api_url \
                        --grafana-key $(cat $api_key_path)
