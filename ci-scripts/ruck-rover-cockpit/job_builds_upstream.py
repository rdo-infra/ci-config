#!/usr/bin/python
import datetime
import time
import requests


ADDITIONAL_JOBS = []
ZUUL_URL = 'http://zuul.openstack.org/'
JOBS_API = ZUUL_URL + 'api/jobs'
BUILDS_API = ZUUL_URL + 'api/builds'
PAGES = 1


# Convert datetime to timestamp
def to_ts(d):
    return datetime.datetime.strptime(d, '%Y-%m-%dT%H:%M:%S').strftime('%s')


def get(url, timeout=20, json_view=True):
    try:
        response = requests.get(url, timeout=timeout)
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
    build_url = BUILDS_API + '?job_name=%s' % job_name
    result = []
    for p in range(pages):
        if p > 0:
            build_url += '&skip=%d' % ((pages - 1) * 50)
            # let's not abuse ZUUL API and sleep betwen requests
            time.sleep(2)
        response = get(build_url)
        result += response
    return result


def influx(build):
    return (
        'build,'
        'pipeline=%s,'
        'branch=%s,'
        'project=%s,'
        'job_name=%s,'
        'voting=%s,'
        'change=%s,'
        'patchset=%s,'
        'passed=%s'
        ' '
        'result=%s,'
        'duration=%s,'
        'start=%s,'
        'end=%s'
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

            1 if build['result'] == 'SUCCESS' else 0,
            build['duration'],
            to_ts(build['start_time']),
            to_ts(build['end_time']),

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
                    print(influx(build))


if __name__ == '__main__':
    main()
