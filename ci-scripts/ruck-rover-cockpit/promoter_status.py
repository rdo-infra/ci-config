#!/bin/env python
import requests
import re
import json
import itertools
import sys
import os
#import feedparser

import pandas as pd
import numpy as np

from bs4 import BeautifulSoup
from launchpadlib.launchpad import Launchpad

import influxdb_utils

promoter_skipping_regex = re.compile(
    '.*promoter Skipping promotion of (.*) to (.*), missing successful jobs:(.*)'
)
promoter_trying_to_regex = re.compile('.*promoter Trying to promote (.*) to (.*)')
promoter_logs_at_regex = re.compile('promoter (.*) at .* logs at (.*)')

def parse_last_promoter_run(release_name):
    promoter_logs = requests.get(
        "http://38.145.34.55/{}.log".format(release_name))
    look_for_promotions = False
    promoter = {}
    last_promotion_name = ''
    last_promotion_status = 'noop'
    promoter_status = ''
    promoter_log = ''
    last_try = ''

    def get_log_time(log_line):
        log_line_splitted = log_line.split()
        log_time = "{} {}".format(log_line_splitted[0], log_line_splitted[1])
        return log_time

    #FIXME: Optimize with a reversed sequence
    for log_line in reversed(list(promoter_logs.iter_lines())):
        if look_for_promotions:
            if 'promoter STARTED' in log_line:
                break
            elif promoter_trying_to_regex.match(log_line):
                #TODO: Not very efficient
                m = promoter_trying_to_regex.match(log_line)
                initial_phase = m.group(1)
                target_phase = m.group(2)
                promoter['promotions'].append({
                    'from': initial_phase,
                    'to': target_phase,
                    'status': last_promotion_status,
                    'logs': 'TODO'
                })
                last_promotion_status = 'noop'
            if last_promotion_status == 'noop':
                if 'SUCCESS promoting' in log_line:
                    last_promotion_status = 'success'
                if 'FAILURE promoting' in log_line:
                    last_promotion_status = 'failure'
                if promoter_skipping_regex.match(log_line):
                    last_promotion_status = 'skipped'

        elif 'ERROR    promoter' in log_line:
            last_try = get_log_time(log_line)
            promoter_status = 'error'
            promoter_log = log_line.split('ERROR    promoter')[1]
            break

        elif 'promoter FINISHED' in log_line:
            last_try = get_log_time(log_line)
            promoter_status = 'finished'
            promoter_log = 'Promoter has finished'
            promoter['promotions'] = []
            look_for_promotions = True

        elif 'promoter STARTED' in log_line:
            last_try = get_log_time(log_line)
            promoter_status = 'ongoing'
            promoter_log = 'The promoter is on going'
            break


    promoter['status'] = promoter_status
    promoter['log'] = promoter_log
    promoter['last_try'] = last_try

    return promoter


def convert_to_influxdb_lines(release, last_promoter_run):
    status_to_severity = {
        'success': 0,
        'ongoing': 0,
        'skipped': 1,
        'noop' : 1,
        'failure': 2,
        'error': 2
    }

    from_stage = ''
    to_stage = ''
    influxdb_lines = []
    prefix = "dlrn-promoter,release={}".format(release)
    # Time format 2018-05-11 11:37:14,061"
    last_try = influxdb_utils.format_ts_from_str(last_promoter_run['last_try'].split(',')[0])


    if 'promotions' in last_promoter_run:
        for promotion in last_promoter_run['promotions']:
            promotion['severity'] = status_to_severity[promotion['status']]
            influxdb_lines.append("{},from={from},to={to} status=\"{status}\",severity={severity},logs=\"{logs}\" {last_try}".format(
                prefix, last_try=last_try, **promotion))
    else:
        last_promoter_run['severity'] = status_to_severity[last_promoter_run['status']]
        influxdb_lines.append("{} status=\"{}\",severity={},logs=\"{}\" {}".format(
            prefix, last_promoter_run['status'], last_promoter_run['severity'], last_promoter_run['log'], last_try))

    return influxdb_lines


def main():
    release = sys.argv[1]
    last_promoter_run = parse_last_promoter_run(release)
    influxdb_lines = convert_to_influxdb_lines(release, last_promoter_run)
    print('\n'.join(influxdb_lines))

if __name__ == '__main__':
    main()
