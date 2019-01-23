#!/usr/bin/env python
import os
import argparse

from launchpadlib.launchpad import Launchpad
from influxdb_utils import format_ts_from_date

cachedir = "{}/.launchpadlib/cache/".format(os.path.expanduser('~'))


def get_bugs(tag, status):
    launchpad = Launchpad.login_anonymously(
        'OOOQ Ruck Rover', 'production', cachedir, version='devel')
    project = launchpad.projects['tripleo']

    # We can filter by status too
    bugs = project.searchTasks(tags=tag, status=status)
    return bugs


def print_as_influxdb(tag, bug_tasks):
    if bug_tasks:
        for bug_task in bug_tasks:
            print(("launchpad-bug,tag={},id={} link=\"{}\""
                   ",title=\"{}\",status=\"{}\",date_created={}").format(
                       tag, bug_task.bug.id, bug_task.web_link,
                       bug_task.bug.title.replace('"', "'").replace(
                           "\\n", "").replace("\\", ""), bug_task.status,
                       format_ts_from_date(bug_task.date_created)))


def main():

    parser = argparse.ArgumentParser(
        description="Print launchpad bugs as influxdb lines")

    parser.add_argument('--tag')
    parser.add_argument('--status', nargs='+',
                        default=['New', 'Triaged', 'In Progress'])
    args = parser.parse_args()

    print_as_influxdb(args.tag, get_bugs(args.tag, args.status))


if __name__ == '__main__':
    main()
