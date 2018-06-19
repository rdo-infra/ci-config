#!/bin/env python
import requests
import re
import json
import sys
import os

import influxdb_utils

promoter_skipping_regex = re.compile(
    '.*promoter Skipping promotion of (.*) from (.*) to (.*), missing successful jobs: (.*)'
)

def parse_skipped_promotions(release_name):
    skipped_promotions = []
    promoter_logs = requests.get(
        "http://38.145.34.55/{}.log".format(release_name))

    def get_log_time(log_line):
        log_line_splitted = log_line.split()
        log_time = "{} {}".format(log_line_splitted[0],log_line_splitted[1])
        log_time = log_time.split(',')[0]
        return log_time

    for log_line in promoter_logs.iter_lines():
        matched_regex = promoter_skipping_regex.match(log_line)
        if matched_regex:
            skipped_promotion = {
                'repo_hash': matched_regex.group(1),
                'from_name': matched_regex.group(2),
                'to_name': matched_regex.group(3),
                'failing_jobs': matched_regex.group(4),
                'timestamp': get_log_time(log_line),
                'release': release_name
            }
            skipped_promotions.append(skipped_promotion)
    return skipped_promotions


def to_influxdb(skipped_promotions):
    influxdb_lines = []
    influxdb_format = ("skipped-promotions,repo_hash={repo_hash},release={release},from_name={from_name},"
                       "to_name={to_name} failing_jobs=\"{failing_jobs}\" "
                       "{timestamp}")

    for skipped_promotion in skipped_promotions:
        skipped_promotion['timestamp'] = influxdb_utils.format_ts_from_str(skipped_promotion['timestamp'])
        influxdb_lines.append(influxdb_format.format(**skipped_promotion))

    return influxdb_lines

def main():
    release = sys.argv[1]
    print('\n'.join(to_influxdb(parse_skipped_promotions(release))))

if __name__ == '__main__':
    main()
