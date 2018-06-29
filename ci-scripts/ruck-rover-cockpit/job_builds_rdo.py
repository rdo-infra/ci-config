#!/usr/bin/python
import datetime
import time
import requests
import yaml

ADDITIONAL_JOBS = []
ZUUL_URL = 'https://review.rdoproject.org/manage/v2/'
JOBS_API = ZUUL_URL + 'jobs/'
BUILDS_API = ZUUL_URL + 'builds/'
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

# software factory job list is slow we take it from zuul's git repo
def get_jobs_list():
    response = requests.get('https://review.rdoproject.org/r/gitweb?p=config.git;a=blob_plain;f=zuul/upstream.yaml;hb=HEAD')
    upstream_jobs = yaml.load(response.content)
    templates = upstream_jobs['project-templates']
    tripleo_jobs = []
    for template in templates:
        for pipeline, jobs in template.iteritems():
            if pipeline is not 'name':
                tripleo_jobs.extend([job for job in jobs if 'tripleo' in job])
    return set(tripleo_jobs)

def get_builds_info(job_name, pages):
    query = {'job_name': job_name, 'order_by': 'start_time', 'desc': 'true'}
    result = []
    for p in range(pages):
        if p > 0:
            query['skip'] = ((pages - 1) * 50)
            # let's not abuse ZUUL API and sleep betwen requests
            time.sleep(2)
        response = get(BUILDS_API, query)
        if response is not None:
            result += response['results']
    return result


def influx(build):
    start_time_from_epoch = to_ts(build['start_time'], seconds=True)
    end_time_from_epoch = to_ts(build['end_time'], seconds=True)
    duration = int(end_time_from_epoch) - int(start_time_from_epoch)
    return (
        'build,'
        'type=rdo,'
        'pipeline=%s,'
        'branch=%s,'
        'project=%s,'
        'job_name=%s,'
        'voting=%s,'
        'change=%s,'
        'patchset=%s,'
        'passed=%s,'
        'cloud=rdo,'
        'region=rdo,'
        'provider=rdo'
        ' '
        'result="%s",'
        'result_num=%s,'
        'log_url="%s",'
        'log_link="%s",'
        'duration=%s,'
        'start=%s,'
        'end=%s,'
        'cloud="rdo",'
        'region="rdo",'
        'provider="rdo"'
        ' '
        '%s' % (
            build['pipeline'],
            "todo", # TODO: Calculate the branch
            build['repository'],
            build['job_name'],
            build['voting'],
            build['change'],
            build['patchset'],

            'True' if build['result'] == 'SUCCESS' else 'False',

            'SUCCESS' if build['result'] == 'SUCCESS' else 'FAILURE',
            1 if build['result'] == 'SUCCESS' else 0,
            build['log_url'],
            "<a href={} target='_blank'>{}</a>".format(build['log_url'], build['job_name']),
            duration,
            start_time_from_epoch,
            end_time_from_epoch,
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
