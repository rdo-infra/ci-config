#!/usr/bin/python

import argparse
import datetime
import time
import requests
import yaml

from diskcache import Cache

OOO_PROJECTS = [
    'openstack/puppet-triple',
    'openstack/python-tripleoclient',
    'openstack/tripleo-upgrade',
    'openstack/tripleo-quickstart-extras',
    'openstack/tripleo-common',
    'openstack-infra/tripleo-ci',
    'openstack/tripleo-quickstart',
    'openstack/tripleo-heat-templates']

TIMESTAMP_PATTERN = '%Y-%m-%dT%H:%M:%S'

cache = Cache('/tmp/ruck_rover_cache')
cache.expire()

# Convert datetime to timestamp


def to_ts(d, seconds=False):
    return datetime.datetime.strptime(
        d, TIMESTAMP_PATTERN).strftime('%s') + (
            '' if seconds else "000000000")


def get(url, query={}, timeout=20, json_view=True):

    try:
        response = requests.get(url, params=query, timeout=timeout)
    except Exception as e:
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
                    cache.add(inventory_path, yaml.load(r.content),
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


def influx(build):

    add_inventory_info(build)

    if build['end_time'] is None:
        build['end_time'] = datetime.datetime.fromtimestamp(
                time.time()).strftime(TIMESTAMP_PATTERN)

    if build['start_time'] is None:
        build['start_time'] = build['end_time']
    # Get the nodename
    return (
        'build,'
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
        'result="%s"'
        ' '
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
        '%s' % (
            build['type'],
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
            1 if build['result'] == 'SUCCESS' else 0,
            build['log_url'],
            "<a href={} target='_blank'>{}</a>".format(
                build['log_url'], build['job_name']),
            build.get('duration', 0),
            to_ts(build['start_time'], seconds=True),
            to_ts(build['end_time'], seconds=True),
            build.get('cloud', 'null'),
            build.get('region', 'null'),
            build.get('provider', 'null'),
            to_ts(build['end_time'])
        )
    )


def print_influx(type, builds):
    if builds:
        for build in builds:
            build['type'] = type
            print(influx(build))


def main():

    parser = argparse.ArgumentParser(
        description="Retrieve as influxdb zuul builds")

    parser.add_argument('--url', default="http://zuul.openstack.org/api/",
                                 help="(default: %(default)s)")
    parser.add_argument('--type', default="upstream",
                                 help="(default: %(default)s)")
    parser.add_argument('--pages', type=int, default=1,
                                 help = "(default: %(default)s)")
    args = parser.parse_args()


    for project in OOO_PROJECTS:
        print_influx(args.type, get_builds_info(url=args.url,
                                     query={'project': project},
                                     pages=args.pages))


if __name__ == '__main__':
    main()
