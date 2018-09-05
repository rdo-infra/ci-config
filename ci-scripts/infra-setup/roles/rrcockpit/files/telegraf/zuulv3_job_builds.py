#!/usr/bin/python

import argparse
import datetime
import time
import requests
import yaml
import json

from diskcache import Cache
from influxdb_utils import format_ts_from_str
from influxdb_utils import format_ts_from_date

OOO_PROJECTS = [
    'openstack/puppet-triple', 'openstack/python-tripleoclient',
    'openstack/tripleo-upgrade', 'openstack/tripleo-quickstart-extras',
    'openstack/tripleo-common', 'openstack-infra/tripleo-ci',
    'openstack/tripleo-quickstart', 'openstack/tripleo-heat-templates'
]

TIMESTAMP_PATTERN = '%Y-%m-%dT%H:%M:%S'
GERRIT_DETAIL_API = "https://review.openstack.org/changes/{}/detail"

cache = Cache('/tmp/ruck_rover_cache')
cache.expire()

# Convert datetime to timestamp


def to_ts(d, seconds=False):
    return datetime.datetime.strptime(
        d, TIMESTAMP_PATTERN).strftime('%s') + ('' if seconds else "000000000")


def get(url, query={}, timeout=20, json_view=True):

    try:
        response = requests.get(url, params=query, timeout=timeout)
    except Exception:
        # add later log file
        pass
    else:
        if response and response.ok:
            if json_view:
                return response.json()
            return response.text
    return None


def get_builds_info(url, query, pages):
    builds = []
    for p in range(pages):
        if p > 0:
            query['skip'] = ((pages - 1) * 50)
            # let's not abuse ZUUL API and sleep betwen requests
            time.sleep(2)
        builds_api = url + "builds"
        response = get(builds_api, query)
        if response is not None:
            builds += response
    return builds


def add_inventory_info(build):

    if 'log_url' in build:
        if build['log_url'].endswith("/html/"):
            build['log_url'] = build['log_url'].replace('html/', '')
        if build['log_url'].endswith("/cover/"):
            build['log_url'] = build['log_url'].replace('cover/', '')
        inventory_path = build['log_url'] + "/zuul-info/inventory.yaml"
        try:
            if inventory_path not in cache:
                r = requests.get(inventory_path)
                if r.ok:
                    cache.add(
                        inventory_path, yaml.load(r.content),
                        expire=259200)  # expire is 3 days

            inventory = cache[inventory_path]
            hosts = inventory['all']['hosts']
            host = hosts[hosts.keys()[0]]
            if 'nodepool' in host:
                nodepool = host['nodepool']
                build['cloud'] = nodepool['cloud']
                build['region'] = nodepool['region']
                build['provider'] = nodepool['provider']

        except Exception:
            pass


def get_timestamp_from_gerrit(build):
    detail_url = GERRIT_DETAIL_API.format(build['change'])
    response = requests.get(detail_url)
    if response.ok:
        sanitized_content = "\n".join(response.content.split("\n")[1:])
        detail = json.loads(sanitized_content)
        for message in detail['messages']:
            if "Patch Set {}".format(
                    build['patchset']
            ) in message['message'] and build['job_name'] in message['message']:
                return format_ts_from_str(message['date'].split('.')[0])
        return format_ts_from_str(detail['updated'].split('.')[0])
    else:
        return format_ts_from_date(time.time())


def influx(build):

    add_inventory_info(build)

    if build['end_time'] is None:
        build['end_time'] = get_timestamp_from_gerrit(build)
    else:
        build['end_time'] = to_ts(build['end_time'], seconds=True)

    if build['start_time'] is None:
        build['start_time'] = build['end_time']
    else:
        build['start_time'] = to_ts(build['start_time'], seconds=True)

    # Get the nodename
    return ('build,'
            'type=%s,'
            'pipeline=%s,'
            'branch=%s,'
            'project=%s,'
            'job_name=%s,'
            'voting=%s,'
            'change=%s,'
            'patchset=%s,'
            'passed=%s,'
            'cloud=%s,'
            'region=%s,'
            'provider=%s,'
            'result=%s'
            ' '
            'result="%s",'
            'result_num=%s,'
            'log_url="%s",'
            'log_link="%s",'
            'duration=%s,'
            'start=%s,'
            'end=%s,'
            'cloud="%s",'
            'region="%s",'
            'provider="%s"'
            ' '
            '%s' %
            (build['type'],
             build['pipeline'],
             'none' if not build['branch'] else build['branch'],
             build['project'],
             build['job_name'],
             build['voting'],
             build['change'],
             build['patchset'],
             'True' if build['result'] == 'SUCCESS' else 'False',
             build.get('cloud', 'null'),
             build.get('region', 'null'),
             build.get('provider', 'null'),
             build['result'],

             build['result'],
             1 if build['result'] == 'SUCCESS' else 0,
             build['log_url'],

             "<a href={} target='_blank'>{}</a>".format(
                 build['log_url'], build['job_name']),
             build.get('duration', 0),
             build['start_time'],
             build['end_time'],
             build.get('cloud', 'null'),
             build.get('region', 'null'),
             build.get('provider', 'null'),

             build['end_time']))


def print_influx(type, builds):
    if builds:
        for build in builds:
            build['type'] = type
            print(influx(build))


def main():

    parser = argparse.ArgumentParser(
        description="Retrieve as influxdb zuul builds")

    parser.add_argument(
        '--url',
        default="http://zuul.openstack.org/api/",
        help="(default: %(default)s)")
    parser.add_argument(
        '--type', default="upstream", help="(default: %(default)s)")
    parser.add_argument(
        '--pages', type=int, default=1, help="(default: %(default)s)")
    args = parser.parse_args()

    for project in OOO_PROJECTS:
        print_influx(
            args.type,
            get_builds_info(
                url=args.url, query={'project': project}, pages=args.pages))


if __name__ == '__main__':
    main()
