#!/usr/bin/env python

import argparse
import requests
import json
from time import time


def find_zuul_queues(zuul_status_url, pipeline_name, queue_name):
    queues = []
    zuul_status = json.loads(requests.get(zuul_status_url).content)

    found_pipeline = next(pipeline['change_queues']
                          for pipeline in zuul_status['pipelines']
                          if pipeline['name'] == pipeline_name)

    found_queues = (queue for queue in found_pipeline
                    if queue_name is None or queue['name'] == queue_name)

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


def convert_builds_as_influxdb(queues):
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
                id = values['id'].split(',')
                values['review'] = id[0]
                values['patch_set'] = id[1]

                influxdb_lines.append(influxdb_line.format(**values))
    return influxdb_lines


def main():

    parser = argparse.ArgumentParser(
        description="Print zuul status as influxdb lines")

    parser.add_argument('--url', required=True)
    parser.add_argument('--pipeline', required=True)
    parser.add_argument('--queue')

    args = parser.parse_args()

    queues = find_zuul_queues(args.url, args.pipeline, args.queue)

    influxdb_lines = convert_builds_as_influxdb(queues)

    print('\n'.join(influxdb_lines))


if __name__ == '__main__':
    main()
