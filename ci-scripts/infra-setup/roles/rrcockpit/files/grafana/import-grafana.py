#!/usr/bin/env python

import argparse
import glob
import json

import requests


def import_file(host, key, path, json_file_path):
    authorization_header = "Bearer {}".format(key)
    headers = {
        'Authorization': authorization_header,
        'Accept': 'application/json',
        'Conent-Type': 'application/json'
    }
    url = "{}/api/{}".format(host, path)
    with open(json_file_path) as json_file:
        print("Importing {}".format(json_file_path))
        data = json.load(json_file)
        response = requests.post(url, headers=headers, json=data)
        if not response.ok:
            if response.status_code == 422:
                raise ValueError("Bad json: {}".format(response.content))
            if path == "dashboards/db" and response.status_code == 412:
                data['overwrite'] = True
                response = requests.post(url, headers=headers, json=data)
                if not response.ok:
                    raise ValueError(response.content)
            elif path == "datasources" and response.status_code == 409:
                # Update it
                id_by_name_url = "{}/id/{}".format(url, data['name'])
                response = requests.get(id_by_name_url, headers=headers)
                id = json.loads(response.content)['id']
                url = "{}/{}".format(url, id)
                response = requests.put(url, headers=headers, json=data)
                if not response.ok:
                    raise ValueError(response.content)
            elif path == "alert-notifications" and response.status_code == 500:
                # Update it
                url = "{}/{}".format(url, data['name'])
                response = requests.put(url, headers=headers, json=data)

                # Grafana alert notifications throw API is not working
                # quite well, let's just print it at least
                if not response.ok:
                    print(response.content)


def main():

    parser = argparse.ArgumentParser(
        description="Export grafana as json files")

    parser.add_argument('--host', default='http://localhost:8080')
    parser.add_argument('--key', default='grafana.key')

    args = parser.parse_args()

    with open(args.key) as key_file:
        key = key_file.read().splitlines()[0]
        for file_path in glob.glob("*.datasource.json"):
            import_file(args.host, key, 'datasources', file_path)

        for file_path in glob.glob("*.dashboard.json"):
            import_file(args.host, key, 'dashboards/db', file_path)

        for file_path in glob.glob("*.alert-notification.json"):
            import_file(args.host, key, 'alert-notifications', file_path)


if __name__ == '__main__':
    main()
