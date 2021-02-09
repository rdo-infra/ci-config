#!/usr/bin/env python

import argparse
import json

import requests


def main():

    json_options = {
        "sort_keys": True,
        "indent": 4,
        "separators": (',', ':')
    }

    parser = argparse.ArgumentParser(
        description="Export grafana as json files")

    parser.add_argument('--host', default='http://localhost:8080')
    parser.add_argument('--key', default='grafana.key')

    args = parser.parse_args()

    with open(args.key) as key_file:
        key = key_file.read().splitlines()[0]
        authorization_header = "Bearer {}".format(key)
        headers = {'Authorization': authorization_header}
        response = requests.get(
            "{}/api/search?query=&".format(args.host),
            headers=headers)

        if response.ok:
            for dashboard_id in response.json():
                print("Exporting dashboard {title}".format(**dashboard_id))
                url = "{host}/api/dashboards/uid/{uid}".format(
                    host=args.host, **dashboard_id)
                dashboard_response = requests.get(url, headers=headers)
                dashboard = dashboard_response.json()
                dashboard_name = dashboard_id['uri'].split('/')[1]
                with open("{}.dashboard.json".format(dashboard_name),
                          'w') as json_file:
                    dashboard.pop('meta', None)
                    dashboard['dashboard'].pop('version', None)
                    dashboard['dashboard'].pop('id', None)
                    dashboard['dashboard'].pop('uid', None)
                    dashboard['dashboard'].pop('iteration', None)
                    text_b = json.dumps(dashboard, **json_options)
                    text_b += "\n"
                    json_file.write(text_b)

            datasources_list = json.loads(
                requests.get("{}/api/datasources".format(args.host),
                             headers=headers).content)
            for datasource_id in datasources_list:
                print("Exporting datasource {name}".format(**datasource_id))
                url = "{host}/api/datasources/{id}".format(
                    host=args.host, **datasource_id)
                datasource_response = requests.get(url, headers=headers)
                datasource = datasource_response.json()
                with open("{name}.datasource.json".format(**datasource_id),
                          'w') as json_file:
                    datasource.pop('id', None)
                    datasource.pop('version', None)
                    json.dump(datasource, json_file, **json_options)

            alert_notifications_list = json.loads(
                requests.get(
                    "{}/api/alert-notifications".format(args.host),
                    headers=headers).content)
            for alert_notification_id in alert_notifications_list:
                print("Exporting alert-notification {name}".format(
                    **alert_notification_id))
                url = "{host}/api/alert-notifications/{id}".format(
                    host=args.host, **alert_notification_id)
                alert_notification_response = requests.get(url,
                                                           headers=headers)
                alert_notification = alert_notification_response.json()
                with open(
                        "{name}.alert-notification.json".format(
                            **alert_notification_id), 'w') as json_file:
                    alert_notification.pop('version', None)
                    alert_notification.pop('created', None)
                    alert_notification.pop('updates', None)
                    alert_notification.pop('updated', None)
                    json.dump(alert_notification, json_file, **json_options)
        else:
            print("Error: {} -> {}".format(response, response.content))
            exit(1)


if __name__ == '__main__':
    main()
