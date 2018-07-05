#!/usr/bin/env python

import argparse
import requests
import json


def main():

    parser = argparse.ArgumentParser(
        description="Export grafana as json files")

    parser.add_argument('--host', required=True)
    parser.add_argument('--key', required=True)

    args = parser.parse_args()

    authorization_header = "Bearer {}".format(args.key)
    headers = {'Authorization': authorization_header}

    dashboards_list = json.loads(
        requests.get(
            "{}/api/search?query=&".format(args.host),
            headers=headers).content)
    for dashboard_id in dashboards_list:
        print("Exporting dashboard {title}".format(**dashboard_id))
        url = "{host}/api/dashboards/uid/{uid}".format(
            host=args.host, **dashboard_id)
        dashboard = json.loads(requests.get(url, headers=headers).content)
        dashboard_name = dashboard_id['uri'].split('/')[1]
        with file("{}.dashboard.json".format(dashboard_name),
                  'w') as json_file:
            dashboard.pop('meta', None)
            dashboard['dashboard'].pop('version', None)
            dashboard['dashboard'].pop('id', None)
            dashboard['dashboard'].pop('uid', None)
            json.dump(dashboard, json_file, indent=4)

    datasources_list = json.loads(
        requests.get("{}/api/datasources".format(args.host),
                     headers=headers).content)
    for datasource_id in datasources_list:
        print("Exporting datasource {name}".format(**datasource_id))
        url = "{host}/api/datasources/{id}".format(
            host=args.host, **datasource_id)
        datasource = json.loads(requests.get(url, headers=headers).content)
        with file("{name}.datasource.json".format(**datasource_id),
                  'w') as json_file:
            datasource.pop('id', None)
            datasource.pop('version', None)
            json.dump(datasource, json_file, indent=4)

    alert_notifications_list = json.loads(
        requests.get(
            "{}/api/alert-notifications".format(args.host),
            headers=headers).content)
    for alert_notification_id in alert_notifications_list:
        print("Exporting alert-notification {name}".format(
            **alert_notification_id))
        url = "{host}/api/alert-notifications/{id}".format(
            host=args.host, **alert_notification_id)
        alert_notification = json.loads(
            requests.get(url, headers=headers).content)
        with file(
                "{name}.alert-notification.json".format(
                    **alert_notification_id), 'w') as json_file:
            alert_notification.pop('id', None)
            alert_notification.pop('version', None)
            alert_notification.pop('created', None)
            alert_notification.pop('updates', None)
            json.dump(alert_notification, json_file, indent=4)


if __name__ == '__main__':
    main()
