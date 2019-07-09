#!/usr/bin/env python

import requests

from influxdb_utils import format_ts_from_str

INFLUXDB_LINE = 'github-status message="{}",status="{}",status_enum={} {}'
STATUS_MAPPING = {'none': 0, 'minor': -1, 'major': -2, 'critical': -3}

# ISO 8601
TIMESTAMP_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


def main():
    r = requests.get("https://kctbh9vrtdwd.statuspage.io/api/v2/status.json")
    if r.ok:
        message = r.json()
        if message:
            print(INFLUXDB_LINE.format(
                message['status']['description'],
                message['status']['indicator'],
                STATUS_MAPPING[message['status']['indicator']],
                format_ts_from_str(message['page']['updated_at'],
                                   TIMESTAMP_FORMAT)))


if __name__ == '__main__':
    main()
