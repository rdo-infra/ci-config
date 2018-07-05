#!/usr/bin/env python

import argparse
import os
import requests
import json
import glob

def import_file(host, key, path, json_file_path):
    authorization_header="Bearer {}".format(key)
    headers={
        'Authorization': authorization_header,
        'Accept': 'application/json',
        'Conent-Type': 'application/json'
    }
    url="{}/api/{}".format(host, path)
    with file(json_file_path) as json_file:
        print("Importing {}".format(json_file_path))
        data = json.load(json_file)
        response = requests.post(url, headers=headers, json=data)
        print(response)
        if not response.ok:
            if path == "dashboards/db" and response.status_code == 412:
                data['overwrite'] = True
                response = requests.post(url, headers=headers, json=data)
                print(response)
            elif path == "datasources" and response.status_code == 409:
                # Update it
                id_by_name_url = "{}/id/{}".format(url, data['name'])
                response = requests.get(id_by_name_url, headers=headers)
                id = json.loads(response.content)['id']
                url = "{}/{}".format(url, id)
                response = requests.put(url, headers=headers, json=data)
                print(response)
            elif path == "alert-notifications" and response.status_code == 500:
                # Update it
                url = "{}/{}".format(url, data['name'])
                response = requests.put(url, headers=headers, json=data)
                print(response)

def main():

    parser = argparse.ArgumentParser(
        description="Export grafana as json files")

    parser.add_argument('--host', required=True)
    parser.add_argument('--key', required=True)

    args = parser.parse_args()

    for file_path in glob.glob("*.dashboard.json"):
       import_file(args.host, args.key, 'dashboards/db', file_path)

    for file_path in glob.glob("*.datasource.json"):
       import_file(args.host, args.key, 'datasources', file_path)

    for file_path in glob.glob("*.alert-notification.json"):
       import_file(args.host, args.key, 'alert-notifications', file_path)

if __name__ == '__main__':
    main()
