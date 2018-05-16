#!/bin/env python

import argparse
import os
import requests
import json

def main():

    parser = argparse.ArgumentParser(
        description="Export grafana as json files")

    parser.add_argument('--host', required=True)
    parser.add_argument('--key', required=True)

    args = parser.parse_args()

    authorization_header="Bearer {}".format(args.key)
    headers={'Authorization': authorization_header}

    dashboards_list = json.loads(requests.get("{}/api/search?query=&".format(args.host), headers=headers).content)

    for dashboard_id in dashboards_list:
        print("Exporting {title} dashboard".format(**dashboard_id))
        url="{host}/api/dashboards/uid/{uid}".format(host=args.host, **dashboard_id)
        dashboard_json=requests.get(url, headers=headers).content

        dashboard_name=dashboard_id['uri'].split('/')[1]
        with file("{}.dashboard.json".format(dashboard_name), 'w') as json_file:
                json_file.write(dashboard_json)


if __name__ == '__main__':
    main()
