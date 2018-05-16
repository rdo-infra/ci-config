#!/bin/env python

import argparse
import requests
import json
import sys
import os

import pprint as pp

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


def convert_builds_as_influxdb(queue):
    # Let's express failures as negative numbers, is easier for alarms
    result_mapping = {
        'FAILURE': -1,
        'None' : 0,
        'SUCCESS': 1,
    }
    influxdb_lines = []
    influxdb_line = "zuul-queue-status,url={url},pipeline={pipeline},queue={queue},job={name},refspec={id} result={result},result_code={result_code} {start_time}"
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
    pp.pprint(queue)
    pp.pprint(influxdb_lines)

if __name__ == '__main__':
    main()
