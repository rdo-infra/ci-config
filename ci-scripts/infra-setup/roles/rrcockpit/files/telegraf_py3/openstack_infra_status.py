#!/usr/bin/env python
import re
from datetime import datetime

import influxdb_utils
import pandas as pd
import requests
from bs4 import BeautifulSoup

infra_status_regexp = re.compile(
    '^ *([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}) *UTC *(.+)$')

infra_status_url = 'https://wiki.openstack.org/wiki/Infrastructure_Status'
infra_status_utc_format = '%Y-%m-%d %H:%M:%S'

pd.set_option('display.max_colwidth', None)


def to_infra_date(date_str):
    return datetime.strptime(date_str, infra_status_utc_format)


def get_infra_issues():
    infra_status = requests.get(infra_status_url)
    infra_status_soup = BeautifulSoup(infra_status.content, 'html.parser')
    raw_issues = infra_status_soup.find_all('li')
    times = []
    issues = []
    for ts_and_issue in raw_issues:
        m = infra_status_regexp.match(ts_and_issue.get_text())
        if m:
            times.append(to_infra_date(m.group(1)))
            issues.append(m.group(2))
    time_and_issue = pd.DataFrame({'time': times, 'issue': issues})
    return time_and_issue.set_index('time')


def convert_to_influxdb_lines(infra_issues):
    formatted = ""
    # TODO: Filter to interested issues
    for index, infra_issue in infra_issues.head().iterrows():
        ts = influxdb_utils.format_ts_from_date(index)
        issue = infra_issue['issue'].replace('"', "'")
        formatted += "openstack-infra-issues issue=\"{}\" {}\n".format(
            issue.encode('utf-8'), ts)
    return formatted


def main():
    print(convert_to_influxdb_lines(get_infra_issues()))


if __name__ == '__main__':
    main()
