#!/usr/bin/env python

import requests

from influxdb_utils import format_ts_from_str

INFLUXDB_LINE = 'github-status message="{}",status="{}",status_enum={} {}'
STATUS_MAPPING = {'good': 0, 'minor': -1, 'major': -2}

# ISO 8601
TIMESTAMP_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


def main():
    r = requests.get("https://status.github.com/api/messages.json")
    if r.ok:
        for message in r.json():
            print(INFLUXDB_LINE.format(
                message['body'], message['status'],
                STATUS_MAPPING[message['status']],
                format_ts_from_str(message['created_on'], TIMESTAMP_FORMAT)))


if __name__ == '__main__':
    main()
