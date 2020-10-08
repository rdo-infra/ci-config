#!/usr/bin/env python

import json
import re
from os import path
from time import time

import click
import requests

CERT_LOCATION = '/etc/pki/tls/certs/ca-bundle.crt'


def find_zuul_queues(zuul_status_url, pipeline_name, queue_name,
                     project_regex):
    queues = []
    # required for internal zuul
    if 'redhat.com' in zuul_status_url:
        if path.exists(CERT_LOCATION):
            cert = CERT_LOCATION
        else:
            cert = False
        zuul_status = json.loads(
            requests.get(
                zuul_status_url,
                verify=cert).content)
    else:
        zuul_status = json.loads(
            requests.get(
                zuul_status_url).content)

    found_pipeline = next(pipeline['change_queues']
                          for pipeline in zuul_status['pipelines']
                          if pipeline['name'] == pipeline_name)

    if queue_name:
        found_queues = (queue for queue in found_pipeline
                        if queue['name'] == queue_name)
    elif project_regex:
        found_queues = (queue for queue in found_pipeline
                        if re.search(project_regex, queue['name']))
    else:
        found_queues = (queue for queue in found_pipeline)

    for queue in found_queues:
        refspecs = []
        queue_heads = queue['heads']
        if queue_heads:
            refspecs = queue_heads[0]
            queues.append({
                'url': zuul_status_url,
                'pipeline': pipeline_name,
                'queue': queue['name'],
                'refspecs': refspecs
            })

    return queues


def calculate_minutes_enqueued(enqueue_time):
    # TODO: Do we have to use start time instead ?
    current_time = int(time() * 1000)
    minutes_enqueued = ((current_time - enqueue_time) / 60000)
    return minutes_enqueued


def convert_builds_as_influxdb(queues, max_time=False):
    # Le's express failures as negative numbers, is easier for alarms

    result_mapping = {
        'ONGOING': 0,
        'SUCCESS': 1,
        'SKIPPED': 1,
    }
    influxdb_lines = []
    influxdb_line = ("zuul-queue-status,url={url},pipeline={pipeline}"
                     ",queue={queue},job={name},review={review}"
                     ",patch_set={patch_set} result=\"{result}\""
                     ",enqueue_time={enqueue_time},"
                     "enqueued_time={enqueued_time},result_code={result_code}")
    lines = []
    for queue in queues:
        for refspec in queue['refspecs']:
            for job in refspec['jobs']:
                # FIXME: Not very performant
                values = {}
                values.update(job)
                values.update(refspec)
                values.update(queue)

                result = values.get('result', 'ONGOING')
                values['result'] = result
                result_code = result_mapping.get(result, -1)

                values['result_code'] = result_code
                values['enqueued_time'] = calculate_minutes_enqueued(
                    values['enqueue_time'])

                # influxdb line protocol uses commas to split stuf,
                # let's escape it
                id_ = values['id'].split(',')
                values['review'] = id_[0]
                values['patch_set'] = id_[1]
                lines.append(values)
    if max_time:
        lines = sorted(lines, key=lambda x: x['enqueued_time'])[-1:]
    for line in lines:
        influxdb_lines.append(influxdb_line.format(**line))
    return influxdb_lines


@click.command()
@click.option('--url', required=True, type=str, default=None)
@click.option('--pipeline', required=True, type=str, default=None)
@click.option('--max_time', is_flag=True, default=False, type=bool)
@click.option('--queue', type=str)
@click.option('--project_regex', type=str)
def main(url=None,
         pipeline=None,
         max_time=False,
         queue=None,
         project_regex=None):

    # this is not really needed, but makes it look more like
    # argsparse
    # args = click.get_current_context().params
    queues = find_zuul_queues(url, pipeline, queue,
                              project_regex)

    influxdb_lines = convert_builds_as_influxdb(queues, max_time=max_time)

    print('\n'.join(influxdb_lines))


if __name__ == '__main__':
    main()
