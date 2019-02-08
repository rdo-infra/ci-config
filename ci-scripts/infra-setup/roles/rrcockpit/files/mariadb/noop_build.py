#!/usr/bin/env python

import argparse
import http_utils
import json
import re

GERRIT_URL = 'https://review.openstack.org'

CI_NAME = {
    'upstream': 'zuul',
    'rdo': 'rdothirdparty'
}

REVIEWS = {
    'master': 560445,
    'rocky': 604293,
    'queens': 567224,
    'pike': 602248
}

BUILD_REGEX = re.compile('^[*-] (?P<job>.*?) (?P<url>.*?) : (?P<result>[^ ]+) '
                                  '?(?P<comment>.*)$')

def get_messages(release):
    review = REVIEWS[release]
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

def compose_as_csv(release, type, builds):
    csv = ""
    for build in builds:
        csv += ('{},{},{},{},{},{},{}\n').format(
            release,
            type,
            build['job'],
            build['url'],
            build['result'],
            1 if build['result'] == 'SUCCESS' else 0,
            build['date'],
            build['comment'])
    return csv

def main():
    parser = argparse.ArgumentParser(
        description="Retrieve as influxdb zuul builds")

    parser.add_argument(
        '--type',
        default="upstream",
        help="(default: %(default)s)")
    parser.add_argument(
        '--release', default="master", help="(default: %(default)s)")

    args = parser.parse_args()

    messages = get_messages(args.release)
    last_message = get_last_message(messages, args.type)
    builds = get_builds(last_message)
    print(compose_as_csv(args.release, args.type, builds))

if __name__ == '__main__':
    main()
