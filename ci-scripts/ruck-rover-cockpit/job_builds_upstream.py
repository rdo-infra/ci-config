#!/usr/bin/python
import datetime
import time
import requests
import yaml
import json

ADDITIONAL_PROJECTS = []
ZUUL_URL = 'http://zuul.openstack.org/api/'
GERRIT_URL = 'https://review.openstack.org/'
PROJECTS_API = GERRIT_URL + 'projects/'
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
    else:
        if response and response.ok:
            if json_view:
                return response.json()
            return response.text
    return None


def get_projects_list():
    project_list_text = get(PROJECTS_API, json_view=False)
    # Gerrit is returning garbage in the first line
    project_list_text = '\n'.join(project_list_text.split('\n')[1:])
    project_list = json.loads(project_list_text)
    ooo_projects = [p for p in project_list if 'tripleo' in p]
    return ooo_projects + ADDITIONAL_PROJECTS


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
        'end=%s'
        ' '
        '%s' % (
            build['pipeline'],
            'none' if not build['branch'] else build['branch'],
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
            to_ts(build['end_time'])
                )
    )


def print_influx(builds):
    if builds:
        for build in builds:

            # FIXME: We don't want to hit log.ooo server too much
            #        let's find another way to access inventory
            #if build['result'] != 'SUCCESS':
            #    add_inventory_info(build, hosts=['primary'])

            print(influx(build))

def main():
    projects = get_projects_list()

    if projects:
        for project in projects:
            print_influx(get_builds_info({'project': project}))

if __name__ == '__main__':
    main()
