#!/usr/bin/python

import argparse
import datetime
import time
import requests
import yaml
import re

from diskcache import Cache

OOO_PROJECTS = [
    'openstack/puppet-triple', 'openstack/python-tripleoclient',
    'openstack/tripleo-upgrade', 'openstack/tripleo-quickstart-extras',
    'openstack/tripleo-common', 'openstack-infra/tripleo-ci',
    'openstack/tripleo-quickstart', 'openstack/tripleo-heat-templates'
]

TIMESTAMP_PATTERN = '%Y-%m-%dT%H:%M:%S'
TIMESTAMP_PATTERN2 = '%Y-%m-%d %H:%M:%S'

JOBS_FOR_ARA = [
    'tripleo-ci-centos-7-standalone',
    'tripleo-ci-centos-7-containers-multinode',
    'tripleo-ci-centos-7-undercloud-containers',
    'tripleo-ci-centos-7-scenario001-multinode-oooq-container',
    'tripleo-ci-centos-7-scenario002-multinode-oooq-container',
    'tripleo-ci-centos-7-scenario003-multinode-oooq-container',
    'tripleo-ci-centos-7-scenario004-multinode-oooq-container',
]

ARA_JSONS = []
#    '/logs/ara.oooq.root.json',
#    '/logs/ara.oooq.oc.json',
#    '/logs/ara.json'
# ]

TASK_DURATION_TRESHOLD = 10

cache = Cache('/tmp/ruck_rover_cache')
cache.expire()

# Convert datetime to timestamp


def to_ts(d, seconds=False, pattern=TIMESTAMP_PATTERN):
    return datetime.datetime.strptime(
        d, pattern).strftime('%s') + ('' if seconds else "000000000")


def to_seconds(duration):
    x = time.strptime(duration, '%H:%M:%S')
    return datetime.timedelta(
        hours=x.tm_hour, minutes=x.tm_min, seconds=x.tm_sec).total_seconds()


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


def get_builds_info(url, query, pages, offset):
    builds = []
    for p in range(pages):
        if p > 0:
            query['skip'] = offset + (p * 50)
            # let's not abuse ZUUL API and sleep betwen requests
            time.sleep(2)
        else:
            query['skip'] = offset
        builds_api = url + "builds"
        response = get(builds_api, query)
        if response is not None:
            builds += response
    return builds


def get_file_from_build(build, file_relative_path):
    if 'log_url' in build:
        if build['log_url'].endswith("/html/"):
            build['log_url'] = build['log_url'].replace('html/', '')
        if build['log_url'].endswith("/cover/"):
            build['log_url'] = build['log_url'].replace('cover/', '')
        file_path = build['log_url'] + file_relative_path
        if file_path not in cache:
            r = requests.get(file_path)
            if r.ok:
                cache.add(
                    file_path, yaml.load(r.content),
                    expire=259200)  # expire is 3 days
            # Add negative cache
            else:
                cache[file_path] = None

        return cache[file_path]


def add_inventory_info(build):
        try:
            inventory = get_file_from_build(build, "/zuul-info/inventory.yaml")
            hosts = inventory['all']['hosts']
            host = hosts[hosts.keys()[0]]
            if 'nodepool' in host:
                nodepool = host['nodepool']
                build['cloud'] = nodepool['cloud']
                build['region'] = nodepool['region']
                build['provider'] = nodepool['provider']

        except Exception:
            pass


def fix_task_name(task_name):
    return re.sub(r'/tmp/tripleo-modify-image.*', '/tmp/tripleo-modify-image',
                  task_name).replace(',', '_')


def print_influx_ara_tasks(build, ara_json_file):
    if build['job_name'] not in JOBS_FOR_ARA:
        return
    try:
        tasks = get_file_from_build(build, ara_json_file)
        if tasks is None:
            return
        for task in tasks:
            duration = to_seconds(task['Duration'])
            if duration > TASK_DURATION_TRESHOLD:
                print("build-task,task_name={},logs_path={},json_path={}"
                      " duration={},job_result=\"{}\",job_branch=\"{}\" {}".
                      format(
                          fix_task_name(task['Name'].replace(' ', '\\ ')),
                          build['log_url'], ara_json_file, duration,
                          build['result'], build['branch'],
                          to_ts(
                              task['Time Start'],
                              seconds=False,
                              pattern=TIMESTAMP_PATTERN2)))

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
            'result="%s"'
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
            (build['type'], build['pipeline'], 'none' if not build['branch']
             else build['branch'], build['project'], build['job_name'],
             build['voting'], build['change'], build['patchset'], 'True'
             if build['result'] == 'SUCCESS' else 'False',
             build.get('cloud', 'null'), build.get('region', 'null'),
             build.get('provider', 'null'), build['result'], build['result'], 1
             if build['result'] == 'SUCCESS' else 0, build['log_url'],
             "<a href={} target='_blank'>{}</a>".format(
                 build['log_url'], build['job_name']), build.get(
                     'duration', 0), to_ts(build['start_time'], seconds=True),
             to_ts(build['end_time'], seconds=True), build.get(
                 'cloud', 'null'), build.get('region', 'null'),
             build.get('provider', 'null'), to_ts(build['end_time'])))


def print_influx(type, builds):
    if builds:
        for build in builds:
            build['type'] = type
            for ara_json in ARA_JSONS:
                print_influx_ara_tasks(build, ara_json)
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
    parser.add_argument(
        '--offset', type=int, default=0, help="(default: %(default)s)")
    args = parser.parse_args()

    for project in OOO_PROJECTS:
        print_influx(
            args.type,
            get_builds_info(
                url=args.url,
                query={'project': project},
                pages=args.pages,
                offset=args.offset))


if __name__ == '__main__':
    main()
