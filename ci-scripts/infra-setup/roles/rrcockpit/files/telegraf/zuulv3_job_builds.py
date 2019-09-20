#!/usr/bin/python

from __future__ import print_function
import argparse
from datetime import datetime, timedelta
import time
import re
import requests
import yaml
import urllib
#import urllib2

import pdb

import logging

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin

from diskcache import Cache

OOO_PROJECTS = [
    'openstack/puppet-tripleo', 'openstack/python-tripleoclient',
    'openstack/tripleo-upgrade', 'openstack/tripleo-quickstart-extras',
    'openstack/tripleo-common', 'openstack/tripleo-ci',
    'openstack/tripleo-quickstart', 'openstack/tripleo-heat-templates',
    'openstack/tripleo-ansible', 'openstack/tripleo-validations',
    'rdo-infra/ansible-role-tripleo-ci-reproducer'
]

TIMESTAMP_PATTERN = '%Y-%m-%dT%H:%M:%S'
TIMESTAMP_PATTERN2 = '%Y-%m-%d %H:%M:%S'

JOBS_FOR_ARA = []
#    'tripleo-ci-centos-7-standalone',
#    'tripleo-ci-centos-7-containers-multinode',
#    'tripleo-ci-centos-7-undercloud-containers',
#    'tripleo-ci-centos-7-scenario001-multinode-oooq-container',
#    'tripleo-ci-centos-7-scenario002-multinode-oooq-container',
#    'tripleo-ci-centos-7-scenario003-multinode-oooq-container',
#    'tripleo-ci-centos-7-scenario004-multinode-oooq-container',
# ]

ARA_JSONS = [
    '/logs/ara.oooq.root.json',
    '/logs/ara.oooq.oc.json',
    '/logs/ara.json'
]

TASK_DURATION_TRESHOLD = 10

cache = Cache('/tmp/ruck_rover_cache')
cache.expire()

# Convert datetime to timestamp


def to_ts(d, seconds=False, pattern=TIMESTAMP_PATTERN):
    return datetime.strptime(
        d, pattern).strftime('%s') + ('' if seconds else "000000000")


def to_seconds(duration):
    x = time.strptime(duration, '%H:%M:%S')
    return datetime.timedelta(
        hours=x.tm_hour, minutes=x.tm_min, seconds=x.tm_sec).total_seconds()


def get(url, json_view, query=None, timeout=20):
    query = query or {}
    try:
        response = requests.get(url, params=query, timeout=timeout)
    except Exception:
        # add later log file
        pass
    else:

        if response and response.ok:
            if json_view:
                return response.json()
            else:
                response.encoding = 'utf-8'
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
        response = get(builds_api, True, query)
        if response is not None:
            builds += response
    return builds


def get_file_from_build(build, file_relative_path, json_view):
    if 'log_url' in build:
        if build['log_url'].endswith("/html/"):
            build['log_url'] = build['log_url'].replace('html/', '')
        if build['log_url'].endswith("/cover/"):
            build['log_url'] = build['log_url'].replace('cover/', '')
        file_path = urljoin(build['log_url'], file_relative_path)

        if file_path not in cache:
            resp = get(file_path, json_view)

            if resp is not None:
                if json_view == True:
                    cache.add(
                        file_path, yaml.safe_load(resp),
                        expire=259200)  # expire is 3 days
                else:
                    cache.add(
                        file_path, resp)
            # Add negative cache
            else:
                cache[file_path] = None

        return cache[file_path]


def add_inventory_info(build, json_view=False):
    try:
        inventory = get_file_from_build(build, "zuul-info/inventory.yaml", json_view)
        inventory = yaml.safe_load(inventory)
        hosts = inventory['all']['hosts']
        host = hosts[hosts.keys()[0]]
        if 'nodepool' in host:
            nodepool = host['nodepool']
            build['cloud'] = nodepool['cloud']
            build['region'] = nodepool['region']
            build['provider'] = nodepool['provider']

    except Exception:
        pass


def add_container_prep_time(build):
    if build['log_url'] is not None:
        job_terms = ['featureset', 'oooq', 'multinode']
        skip_terms = ['update', 'upgrade', 'rocky']
        skip_branch = ['stable/rocky', 'stable/queens']

        if any(x in build['job_name'] for x in skip_terms):
            build['container_prep_time'] = 0
            return build
        elif any(x in build['branch'] for x in skip_branch):
            build['container_prep_time'] = 0
            return build
        elif any(x in build['job_name'] for x in job_terms):
            file_relative_path = "logs/undercloud/home/zuul/install-undercloud.log.txt.gz"
            respData = get_file_from_build(build, file_relative_path, json_view=False)
        elif 'standalone' in build['job_name']:
            file_relative_path = "logs/undercloud/home/zuul/standalone_deploy.log.txt.gz"

            respData = get_file_from_build(build, file_relative_path, json_view=False)
        else:
            build['container_prep_time'] = 0
            return build

        if respData is None:
            build['container_prep_time'] = -1
            return build

        # loop through the file looking for the container prep
        # signature
        count = 0
        container_prep_begin = ""
        container_prep_end = ""
        container_prep_line = 'tripleo-container-image-prepare.log'
        match=""
        for line in respData.splitlines():
            count += 1
            try:
                match = re.search(r'.*'+container_prep_line+'.*',str(line))
            except Exception:
                build['container_prep_time'] = -1
                return build
            if match:
                container_prep_begin = \
                    "-".join(line.decode("utf-8").split(" ")[0:2])
                count = count + 2
                end_line = respData.splitlines()[count]
                container_prep_end = \
                    "-".join(end_line.decode("utf-8").split(" ")[0:2])
                break
        try:
            begin = datetime.strptime(container_prep_begin, '%Y-%m-%d-%H:%M:%S.%f' )
            end = datetime.strptime(container_prep_end, '%Y-%m-%d-%H:%M:%S.%f' )
            prep_container_time = end - begin
            build['container_prep_time'] = prep_container_time.seconds
        except ValueError as err:
            try:
                begin = datetime.strptime(container_prep_begin, '%Y-%m-%d-%H:%M:%S' )
                end = datetime.strptime(container_prep_end, '%Y-%m-%d-%H:%M:%S' )
                prep_container_time = end - begin
                build['container_prep_time'] = prep_container_time.seconds
            except ValueError as err:
                build['container_prep_time'] = -1
                return build


def fix_task_name(task_name):
    return re.sub(r'/tmp/tripleo-modify-image.*', '/tmp/tripleo-modify-image',
                  task_name).replace(',', '_')


def print_influx_ara_tasks(build, ara_json_file):
    if build['job_name'] not in JOBS_FOR_ARA:
        return
    try:
        tasks = get_file_from_build(build, ara_json_file, json_view=True)
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
    add_container_prep_time(build)

    if 'container_prep_time' not in build:
        build['container_prep_time'] = 0

    if build['end_time'] is None:
        build['end_time'] = datetime.datetime.fromtimestamp(
            time.time()).strftime(TIMESTAMP_PATTERN)

    if build['start_time'] is None:
        build['start_time'] = build['end_time']
    duration = build.get('duration', 0)
    if duration is None:
        duration = 0
    # Get the nodename
    return ('build,'
            'container_prep_time=%s,'
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
            (build['container_prep_time'], build['type'],
             build['pipeline'], 'none' if not build['branch']
             else build['branch'], build['project'], build['job_name'],
             build['voting'], build['change'], build['patchset'], 'True'
             if build['result'] == 'SUCCESS' else 'False',
             build.get('cloud', 'null'), build.get('region', 'null'),
             build.get('provider', 'null'), build['result'], build['result'], 1
             if build['result'] == 'SUCCESS' else 0, build['log_url'],
             "<a href={} target='_blank'>{}</a>".format(
                 build['log_url'], build['job_name']),
             duration,
             to_ts(build['start_time'], seconds=True),
             to_ts(build['end_time'], seconds=True), build.get(
                 'cloud', 'null'), build.get('region', 'null'),
             build.get('provider', 'null'), to_ts(build['end_time'])))


def print_influx(build_type, builds):
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger = logging.getLogger()
    logger.addHandler(logging.FileHandler('/tmp/ruck_rover_cache/zuulv3_build.log', 'a'))
    print = logger.info
    if builds:
        for build in builds:
            build['type'] = build_type
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