#!/usr/bin/python
import datetime
import time
import requests
import yaml

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


def get_builds_info(job_name, pages):
    query = {'job_name': job_name}
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

def add_inventory_info(build):
    if 'log_url' in build:
        r = requests.get(build['log_url'] + "/zuul-info/inventory.yaml")
        if r.ok:
            inventory = yaml.load(r.content)
            # FIXME: Primary is enough ?
            build['inventory'] = inventory



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


def main():
    jobs = get_jobs_list()
    if jobs:
        for job in jobs:
            builds = get_builds_info(job, pages=PAGES)
            if builds:
                for build in builds:
                    if build['result'] != 'SUCCESS':
                        add_inventory_info(build)
                    print(influx(build))


if __name__ == '__main__':
    main()
