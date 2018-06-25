#!/usr/bin/python
import datetime
import time
import requests
import yaml

NOOP_CHANGES = ['560445', '567224', '564285', '564291']
ADDITIONAL_JOBS = []
ZUUL_URL = 'http://zuul.openstack.org/api/'
JOBS_API = ZUUL_URL + 'jobs'
BUILDS_API = ZUUL_URL + 'builds'
PAGES = 1

# Convert datetime to timestamp
def to_ts(d, seconds=False):
    return datetime.datetime.strptime(
        d, '%Y-%m-%dT%H:%M:%S').strftime('%s') + (
            '' if seconds else "000000000")


def get(url, query={}, timeout=20, json_view=True):

    try:
        response = requests.get(url, params=query, timeout=timeout)
    except Exception as e:
        # add later log file
        pass
    if response and response.ok:
        if json_view:
            return response.json()
        return response.text
    return None


def get_jobs_list():
    jobs_list = get(JOBS_API)
    ooo_jobs = [i['name'] for i in jobs_list if 'tripleo' in i['name']]
    return ooo_jobs + ADDITIONAL_JOBS


def get_builds_info(query, pages=PAGES):
    result = []
    for p in range(pages):
        if p > 0:
            query['skip'] = ((pages - 1) * 50)
            # let's not abuse ZUUL API and sleep betwen requests
            time.sleep(2)
        response = get(BUILDS_API, query)
        if response is not None:
            result += response
    return result

def add_inventory_info(build, hosts):
    if 'log_url' in build:
        try:
            r = requests.get(build['log_url'] + "/zuul-info/inventory.yaml")
            if r.ok:
                inventory = yaml.load(r.content)
                # FIXME: Primary is enough ?
                if all(host in inventory['all']['hosts'] for host in hosts):
                    build['inventory'] = inventory
        except Exception:
            pass

def influx(build):
    if build['start_time'] == None:
        build['start_time'] = build['end_time']

    # Get the nodename
    return (
        'build,'
        'type=upstream,'
        'pipeline=%s,'
        'branch=%s,'
        'project=%s,'
        'job_name=%s,'
        'voting=%s,'
        'change=%s,'
        'patchset=%s,'
        'passed=%s'
        ' '
        'result="%s",'
        'result_num=%s,'
        'log_url="%s",'
        'log_link="%s",'
        'duration=%s,'
        'start=%s,'
        'end=%s,'
        'primary_node_cloud="%s",'
        'primary_node_region="%s"'
        ''
        ' '
        '%s' % (
            build['pipeline'],
            build['branch'],
            build['project'],
            build['job_name'],
            build['voting'],
            build['change'],
            build['patchset'],

            'True' if build['result'] == 'SUCCESS' else 'False',

            'SUCCESS' if build['result'] == 'SUCCESS' else 'FAILURE',
            1 if build['result'] == 'SUCCESS' else 0,
            build['log_url'],
            "<a href={} target='_blank'>{}</a>".format(build['log_url'], build['job_name']),
            build.get('duration', 0),
            to_ts(build['start_time'], seconds=True),
            to_ts(build['end_time'], seconds=True),
            'null' if 'inventory' not in build else build['inventory']
                ['all']['hosts']['primary']['nodepool']['cloud'],
            'null' if 'inventory' not in build else build['inventory']
                ['all']['hosts']['primary']['nodepool']['region'],
            to_ts(build['end_time'])
                )
    )


def print_influx(builds):
    if builds:
        for build in builds:
            if build['result'] != 'SUCCESS':
                add_inventory_info(build, hosts=['primary'])
            print(influx(build))

def main():
    jobs = get_jobs_list()
    builds = []
    if jobs:
        for job in jobs:
            for build in get_builds_info({'job_name': job}):
                # Filter by noop, we are going to print them later
                # so we don't exclude any job for them
                if build['change'] not in NOOP_CHANGES:
                    builds.append(build)

    for noop_change in NOOP_CHANGES:
        builds += get_builds_info({'change': noop_change})

    print_influx(builds)

if __name__ == '__main__':
    main()
