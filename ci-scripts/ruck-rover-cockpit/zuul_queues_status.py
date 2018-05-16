#!/bin/env python
import requests
import re
import json
import itertools
import sys
import os

from datetime import timedelta

import pandas as pd
import numpy as np

from datetime import datetime, timedelta
from time import time


upstream_zuul_url = 'http://zuul.openstack.org/status'
rdo_zuul_url = 'https://review.rdoproject.org/zuul/status.json'

pd.set_option('display.max_colwidth', -1)

def get_zuul_queue(zuul_status_url, pipeline_name, queue_name):
    zuul_status = json.loads(requests.get(zuul_status_url).content)
    change_queues = [pipeline['change_queues'] for pipeline in zuul_status['pipelines'] if pipeline['name'] == pipeline_name]
    queue = pd.DataFrame()
    if change_queues:
        pipeline_queues = change_queues[0]
        if pipeline_queues:
            found_queue = [queue for queue in pipeline_queues if queue['name'] == queue_name]
            if found_queue:
                queue_heads = found_queue[0]['heads']
                if queue_heads:
                    queue = pd.DataFrame(queue_heads[0])
    return queue


def get_oldest_zuul_job(queue):
    if 'enqueue_time' in queue:
        return queue.sort_values(by=['enqueue_time']).iloc[0]
    return pd.Series()

def get_minutes_enqueued(zuul_job):
    if not zuul_job.empty:
        current_time=int(time() * 1000)
        enqueue_time=zuul_job['enqueue_time']
        minutes_enqueued=((current_time - enqueue_time) / 60000)
        return minutes_enqueued
    else:
        return 0

def format_enqueue_time(minutes_enqueued):
    if minutes_enqueued > 0:
        return "{} hours".format(str(timedelta(minutes=int(minutes_enqueued)))[:-3])
    else:
        return "Empty"

def convert_enqueued_time_to_influxdb(pipeline_name, queue_name, enqueued_time):
    return "zuul,pipeline={},queue={} enqueued_time={}".format(
                pipeline_name, queue_name, enqueued_time)

def print_queue_as_influxdb(zuul_url, pipeline_name, queue_name):
    minutes_enqueued = get_minutes_enqueued(
        get_oldest_zuul_job(
            get_zuul_queue(
                zuul_url,
                pipeline_name,
                queue_name)))
    print(convert_enqueued_time_to_influxdb(
            pipeline_name,
            queue_name,
            minutes_enqueued))

def main():

    print_queue_as_influxdb(
        upstream_zuul_url,
        pipeline_name='gate',
        queue_name='tripleo')

    print_queue_as_influxdb(
        rdo_zuul_url,
        pipeline_name='openstack-periodic-24hr',
        queue_name='openstack-infra/tripleo')

if __name__ == '__main__':
    main()
