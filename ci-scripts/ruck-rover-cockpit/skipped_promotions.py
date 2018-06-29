#!/bin/env python
import requests
import re
import json
import sys
import os
import dlrnapi_client
import influxdb_utils

from promoter_utils import get_dlrn_instance_for_release
from diskcache import Cache

cache = Cache('/tmp/ruck_rover_cache')
cache.expire()

promoter_skipping_regex = re.compile(
    '.*promoter Skipping promotion of (.*) from (.*) to (.*), missing successful jobs: (.*)'
)


def get_failing_jobs_html(dlrn_hashes, release_name):
    failing_jobs_html = ""
    try:
        dlrn = get_dlrn_instance_for_release(release_name)
        if dlrn:
            params = dlrnapi_client.Params2()
            params.commit_hash = dlrn_hashes['commit_hash']
            params.distro_hash = dlrn_hashes['distro_hash']
            params.success = str(False)
            failing_jobs = dlrn.api_repo_status_get(params)
            print(dlrn_hashes['repo_hash'])
            print(failing_jobs)
            for failing_job in failing_jobs:
                failing_job_html = "<a href='{}' target='_blank' >{}</a><br>".format(failing_job.url,
                                                                                         failing_job.job_id)
                failing_jobs_html += failing_job_html
    except Exception as e:
        pass
    return failing_jobs_html

# FIXME: Use a decorator ?
def get_cached_failing_jobs_html(dlrn_hashes, release_name):
    cache_key = "failing_jobs_html_{timestamp}_{repo_hash}".format(**dlrn_hashes)
    if cache_key not in cache or dlrn_hashes['repo_hash'] == "3a06aedd82dd5ed609c9371dada9f75cf3692008_8d0f9fd1":
        failing_jobs_html = get_failing_jobs_html(dlrn_hashes,
                                                    release_name)
        cache.add(cache_key, failing_jobs_html, expire=259200)
    return cache[cache_key]

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

            promotion = matched_regex.group(1)
            try:
                promotion = eval(matched_regex.group(1))
                repo_hash = promotion['repo_hash']
                failing_jobs = get_cached_failing_jobs_html(promotion,
                                                            release_name)
            except Exception:
                repo_hash = promotion
                failing_jobs = matched_regex.group(3)

            skipped_promotion = {
                'repo_hash': repo_hash,
                'from_name': matched_regex.group(2),
                'to_name': matched_regex.group(3),
                'failing_jobs': failing_jobs,
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
    influxdb_lines = to_influxdb(parse_skipped_promotions(release))
    #print('\n'.join(influxdb_lines))

if __name__ == '__main__':
    main()
