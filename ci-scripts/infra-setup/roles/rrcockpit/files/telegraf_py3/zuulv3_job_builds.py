#!/usr/bin/python

import argparse
import re
import time
from datetime import datetime

import requests
import urllib3
import yaml
from diskcache import Cache

urllib3.disable_warnings()

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin


OOO_PROJECTS = [
    'openstack/puppet-tripleo', 'openstack/python-tripleoclient',
    'openstack/tripleo-upgrade', 'openstack/tripleo-quickstart-extras',
    'openstack/tripleo-common', 'openstack/tripleo-ci',
    'openstack/tripleo-quickstart', 'openstack/tripleo-heat-templates',
    'openstack/tripleo-ansible', 'openstack/tripleo-validations',
    'rdo-infra/ansible-role-tripleo-ci-reproducer',
    'containers/libpod', 'ceph/ceph-ansible',
    'openstack/ansible-collections-openstack', 'openstack/heat',
    'rdoinfo', 'nfvinfo'
]

INTERNAL_OOO_PROJECTS = [
    'openstack/tripleo-ci-internal-jobs',
    'rhos-release',
    'openstack-tempest',
    'openstack-tripleo-common',
    'openstack-tripleo-heat-templates-compat',
    'openstack-tripleo-heat-templates',
    'openstack-tripleo-image-elements',
    'openstack-tripleo-puppet-elements',
    'openstack-tripleo-ui',
    'openstack-tripleo-validations',
    'openstack-tripleo',
    'openstack/tripleo-ci',
    'rhos-ops/openstack-tripleo-heat-templates'
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
CACHE_EXPIRE_SECS = 604800  # a week
CACHE_SIZE = int(2e9)  # 2GB

cache = Cache('/tmp/ruck_rover_cache', size_limit=CACHE_SIZE)
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
        response = requests.get(url,
                                params=query,
                                timeout=timeout,
                                verify=False)
        if response and response.ok:
            if json_view:
                return response.json()
            else:
                response.encoding = 'utf-8'
                return response.text
    except Exception:
        return None

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
        if "rdo" in url:
            builds_api = url + "builds"
        else:
            builds_api = url + "builds" + '?complete=true'
        response = get(builds_api, True, query)
        if response is not None:
            builds += response
    return builds


def get_file_from_build(build, file_relative_path, json_view):
    if 'log_url' in build and build['log_url']:
        if build['log_url'].endswith("/html/"):
            build['log_url'] = build['log_url'].replace('html/', '')
        if build['log_url'].endswith("/cover/"):
            build['log_url'] = build['log_url'].replace('cover/', '')
        file_path = urljoin(build['log_url'], file_relative_path)

        if file_path not in cache:
            resp = get(file_path, json_view)

            if resp is not None:
                if json_view:
                    cache.add(
                        file_path, yaml.safe_load(resp),
                        expire=CACHE_EXPIRE_SECS)
                else:
                    cache.add(file_path, resp)
            # Add negative cache
            else:
                cache[file_path] = None

        return cache[file_path]


def add_inventory_info(build, json_view=False):
    try:
        inventory = get_file_from_build(build,
                                        "zuul-info/inventory.yaml",
                                        json_view)
        inventory = yaml.safe_load(inventory)
        hosts = inventory['all']['hosts']
        host = hosts[list(hosts.keys())[0]]
        if 'nodepool' in host:
            nodepool = host['nodepool']
            build['cloud'] = nodepool['cloud']
            build['region'] = nodepool['region']
            build['provider'] = nodepool['provider']

    except Exception:
        pass


def add_sova_info(build, json_view=False):
    try:
        failures_file = get_file_from_build(build,
                                            "logs/failures_file",
                                            json_view)
        lines = failures_file.split('\n')
        reason = lines[0]
        tag = lines[1].split("Reason: ")[1]
        # Cut long reasons and remove quotes
        build['sova_reason'] = reason[:200].replace('"', '')
        build['sova_tag'] = tag.replace('"', '')
    except Exception:
        pass


# rdoinfo and nfvinfo job meta re which package is updated
def add_rdopkg_change(build, json_view=False):
    rdo_file = "logs/tested_pkgs_updates.txt.gz"
    rdo_project = ["rdoinfo", "nfvinfo"]
    rpm_change_file = ""

    if build['type'] == "rdo" and build['project'] in rdo_project:
        file = rdo_file
        try:
            rpm_change_file = get_file_from_build(build,
                                                  file,
                                                  json_view)
            rpm_change_file = rpm_change_file.splitlines()
        except Exception:
            pass
        if rpm_change_file:
            build['dep_change'] = " ".join(rpm_change_file)


def add_container_prep_time(build):
    if build['log_url'] is not None:
        job_terms = ['featureset', 'oooq', 'multinode']
        skip_terms = ['update', 'upgrade', 'rocky']
        skip_branch = ['stable/rocky', 'stable/queens']

        if any(x in build['job_name'] for x in skip_terms):
            return
        elif any(x in build['branch'] for x in skip_branch):
            return
        elif any(x in build['job_name'] for x in job_terms):
            file_relative_path = ("logs/undercloud/home/zuul/"
                                  "install-undercloud.log.txt.gz")
            resp_data = get_file_from_build(
                build, file_relative_path,
                json_view=False)
        elif 'standalone' in build['job_name']:
            file_relative_path = ("logs/undercloud/home/zuul/"
                                  "standalone_deploy.log.txt.gz")

            resp_data = get_file_from_build(
                build, file_relative_path,
                json_view=False)
        else:
            return

        if resp_data is None:
            return

        # This is the old regular expression, commented here because it's hard
        # to remember
        # container_prep_line = (r'(\d{4}-\d{2}-\d{2}\s(?:[01]\d|2[0-3]):'
        #                        r'(?:[0-5]\d):(?:[0-5]\d))\s\|.*(tripleo-'
        #                        r'container-image-prepare.log).*\n^.*(\d{4}-'
        #                        r'\d{2}-\d{2}\s(?:[01]\d|2[0-3]):(?:[0-5]\d):'
        #                        r'(?:[0-5]\d))\s\|\schanged')
        # For example:
        # 2019-09-23 09:57:04 | TASK [tripleo-container-image-prepare :
        # Run tripleo-container-image-prepare logged to: /var/log/tripleo-
        # container-image-prepare.log] ***\n
        # 2019-09-23 10:15:25 | changed: [undercloud]

        # This is the previous regular expression.
        # Example:
        # 2019-09-30 08:51:23 | tripleo-container-image-prepare :
        # Run tripleo-container-image-prepare logged to:
        # /var/log/tripleo-container-image-prepare.log  4335.64s

        # container_prep_line = (r'\d{4}-\d{2}-\d{2}\s(?:[01]\d|2[0-3])'
        #                        r':(?:[0-5]'
        #                        r'\d):(?:[0-5]\d)\s\|.*tripleo-container-image'
        #                        r'-prepare.log\s*([1-9]*\.?[1-9]*)s')

        # The regex below matches the new Warning log and the previous one
        # where the regex commented above also match

        container_prep_line = (r'Run.*tripleo-container-image-prepare.log'
                               r'\s*\-?\s*([1-9]*\.?[1-9]*)s')

        match = re.findall(container_prep_line, resp_data, re.MULTILINE)

        if len(match) > 0:
            build['container_prep_time_u'] = float(match[0])


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
    # add_container_prep_time(build)
    add_sova_info(build)
    add_rdopkg_change(build)

    if build['end_time'] is None:
        build['end_time'] = datetime.fromtimestamp(
            time.time()).strftime(TIMESTAMP_PATTERN)

    if build['start_time'] is None:
        build['start_time'] = build['end_time']
    duration = build.get('duration', 0)
    if duration is None:
        duration = 0
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
            'provider="%s",'
            'sova_reason="%s",'
            'sova_tag="%s",'
            'dep_change="%s",'
            'container_prep_time_u=0'
            ' '
            '%s' %
            (build['type'],
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
             build.get('provider', 'null'),
             build.get('sova_reason', ''),
             build.get('sova_tag', ''),
             build.get('dep_change', ''),
             to_ts(build['end_time'])))


def print_influx(build_type, builds):
    if builds:
        for build in builds:
            if build['result'] is not None:
                build['type'] = build_type
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

    if args.type == 'internal':
        report_projects = INTERNAL_OOO_PROJECTS
    else:
        report_projects = OOO_PROJECTS

    for project in report_projects:
        print_influx(
            args.type,
            get_builds_info(
                url=args.url,
                query={'project': project},
                pages=args.pages,
                offset=args.offset))


if __name__ == '__main__':
    main()
