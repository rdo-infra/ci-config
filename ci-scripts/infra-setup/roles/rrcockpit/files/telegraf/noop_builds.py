#!/usr/bin/env python

import argparse
import json
import re

import http_utils

from influxdb_utils import format_ts_from_str

GERRIT_URL = 'https://review.openstack.org'

CI_NAME = {
    'upstream': 'zuul',
    'rdo': 'rdothirdparty'
}

REVIEWS = {
    'master': 560445,
    'stable/rocky': 604293,
    'stable/queens': 567224,
    'stable/pike': 602248
}

BUILD_REGEX = re.compile('^[*-] (?P<job>.*?) (?P<url>.*?) : (?P<result>[^ ]+) '
                                  '?(?P<comment>.*)$')

def get_messages(branch):
    review = REVIEWS[branch]
    detail_url = "{}/changes/{}/detail".format(GERRIT_URL, review)
    response = http_utils.get(url=detail_url, json_view=False)
    sanitized_content = "\n".join(response.split("\n")[1:])
    detail = json.loads(sanitized_content)
    return detail['messages']

def get_last_message(messages, type):
    for message in reversed(messages):
        if message['author']['username'] == CI_NAME[type]:
            return message
    return None

def get_builds(message):
    builds = []
    for line in message['message'].splitlines():
        match = BUILD_REGEX.match(line)
        if match:
            build = {}
            build['job'] = match.group('job')
            build['url'] = match.group('url')
            build['result'] = match.group('result')
            build['comment'] = match.group('comment')
            build['date'] = message['date']
            builds.append(build)
    return builds

def compose_as_influxdb(branch, type, builds):
    influxdb = ""
    for build in builds:
        if "non-voting" not in build['comment']:
            influxdb += ('noop,'
                    'branch={},'
                    'type={},'
                    'job={} '
                    'logs="{}",'
                    'result="{}",'
                    'success={},'
                    'comment="{}" '
                    '{}\n').format(
                branch,
                type,
                build['job'],
                build['url'],
                build['result'],
                1 if build['result'] == 'SUCCESS' else 0,
                build['comment'], 
                format_ts_from_str(build['date'].split('.')[0]))
    return influxdb

def main():
    parser = argparse.ArgumentParser(
        description="Retrieve as influxdb zuul builds")

    parser.add_argument(
        '--type',
        default="upstream",
        help="(default: %(default)s)")
    parser.add_argument(
        '--branch', default="master", help="(default: %(default)s)")

    args = parser.parse_args()

    messages = get_messages(args.branch)
    last_message = get_last_message(messages, args.type)
    builds = get_builds(last_message)
    print(compose_as_influxdb(args.branch, args.type, builds))

if __name__ == '__main__':
    main()
