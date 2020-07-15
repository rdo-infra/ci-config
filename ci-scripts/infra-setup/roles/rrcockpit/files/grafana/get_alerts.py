#!/bin/env python

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
    for alert_meta in call_alerts_api(host, key, "?state=alerting"):
        alert = call_alerts_api(host, key, "/{}".format(alert_meta['id']))
        alert.update(alert_meta)
        alerts.append(alert)
    return alerts


def main():

    parser = argparse.ArgumentParser(
        description="Export grafana as json files")

    parser.add_argument('--host', required=True)
    parser.add_argument('--key', required=True)

    args = parser.parse_args()

    for alert in get_alerts(args.host, args.key):
        print(alert)


if __name__ == '__main__':
    main()
