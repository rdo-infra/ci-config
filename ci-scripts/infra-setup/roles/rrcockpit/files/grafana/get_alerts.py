#!/usr/bin/python3

import argparse
import json

import requests


def call_alerts_api(host, key, suffix):
    authorization_header = "Bearer {}".format(key)
    headers = {'Authorization': authorization_header}
    return json.loads(
        requests.get("{}/api/alerts{}".format(host, suffix),
                     headers=headers).content)


def get_alerts(host, key):
    alerts = []
    all_alerts = call_alerts_api(host, key, "?state=alerting")
    if isinstance(all_alerts, list):
        for alert_meta in all_alerts:
            alert = call_alerts_api(host, key, "/{}".format(alert_meta['id']))
            alert.update(alert_meta)
            alerts.append(alert)
    else:
        message = str(all_alerts)
        raise Exception(message)
    return alerts


def post_alert_irc(server, port, alert):
    url = "http://{}:{}".format(server, port)
    this_alert = {}
    this_alert['title'] = alert['name']
    this_alert['message'] = alert['Message']
    this_alert['state'] = 'alerting'
    this_alert = json.dumps(this_alert)
    req = requests.post(url, data=this_alert)
    if req.status_code != 200:
        raise Exception("Post to flask failed")


def main():

    parser = argparse.ArgumentParser(
        description="Export grafana as json files")

    parser.add_argument('--host', required=True)
    parser.add_argument('--key', required=True)

    args = parser.parse_args()

    for alert in get_alerts(args.host, args.key):
        print(alert)
        post_alert_irc("0.0.0.0", "5000", alert)


if __name__ == '__main__':
    main()
