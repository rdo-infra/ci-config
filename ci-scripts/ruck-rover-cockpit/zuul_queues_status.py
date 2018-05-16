#!/bin/env python

import argparse
import requests
import json
import sys
import os
from time import time

from influxdb_utils import format_ts_from_float

def get_zuul_queue(zuul_status_url, pipeline_name, queue_name):
    refspecs = []
    zuul_status = json.loads(requests.get(zuul_status_url).content)
    change_queues = [pipeline['change_queues'] for pipeline in zuul_status['pipelines'] if pipeline['name'] == pipeline_name]
    if change_queues:
        pipeline_queues = change_queues[0]
        if pipeline_queues:
            found_queue = [queue for queue in pipeline_queues if queue['name'] == queue_name]
            if found_queue:
                queue_heads = found_queue[0]['heads']
                if queue_heads:
                    refspecs = queue_heads[0]
    return {
        'url': zuul_status_url,
        'pipeline': pipeline_name,
        'queue': queue_name,
        'refspecs': refspecs
    }

def calculate_minutes_enqueued(enqueue_time):
     # TODO: Do we have to use start time instead ?
     current_time=int(time() * 1000)
     minutes_enqueued=((current_time - enqueue_time) / 60000)
     return minutes_enqueued

def convert_builds_as_influxdb(queue):
    # Let's express failures as negative numbers, is easier for alarms

    result_mapping = {
        'FAILURE': -1,
        'None' : 0,
        'SUCCESS': 1,
    }
    influxdb_lines = []
    #influxdb_line = "zuul-queue-status,url={url},pipeline={pipeline},queue={queue},job={name},refspec={id} result={result},result_code={result_code} {ts}"
    influxdb_line = "zuul-queue-status,url={url},pipeline={pipeline},queue={queue},job={name},refspec={refspec} result=\"{result}\",enqueue_time={enqueue_time},enqueued_time={enqueued_time},result_code={result_code}"
    for refspec in queue['refspecs']:
        for job in refspec['jobs']:
            # FIXME: Not very performant
            values = {}
            values.update(job)
            values.update(refspec)
            values.update(queue)

            result = values['result']
            if result is not None:
                result_code = result_mapping[result]
            else:
                result_code = result_mapping['None']

            values['result_code'] = result_code
            values['enqueued_time'] = calculate_minutes_enqueued(
                        values['enqueue_time'])

            # FIXME: Don't clear view of what to do with influxdb ts
            # values['ts'] = values['enqueue_time'] * 1000000

            # influxdb line protocol uses commas to split stuf, let's escape it
            values['refspec'] = values['id'].replace(',','\\,')

            influxdb_lines.append(influxdb_line.format(**values))
    return influxdb_lines
def main():

    parser = argparse.ArgumentParser(
                description="Inject zuul's staus as influxdb")

    parser.add_argument('--url', required=True)
    parser.add_argument('--pipeline', required=True)
    parser.add_argument('--queue', required=True)

    args = parser.parse_args()

    queue = get_zuul_queue(
        args.url,
        args.pipeline,
        args.queue)


    influxdb_lines = convert_builds_as_influxdb(queue)

    print('\n'.join(influxdb_lines))

if __name__ == '__main__':
    main()
