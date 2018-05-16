#!/bin/env python
import requests
import re
import json
import os
import argparse

from launchpadlib.launchpad import Launchpad

cachedir = "{}/.launchpadlib/cache/".format(os.path.expanduser('~'))

def get_bugs(tags, status):
    launchpad = Launchpad.login_anonymously('OOOQ Ruck Rover', 'production', cachedir, version='devel')
    project = launchpad.projects['tripleo']

    # We can filter by status too
    bugs = project.searchTasks(tags=tags, status=status)
    return bugs

def format_bugs(bugs):
    formatted = []
    for bug in bugs:
        formatted.append({'link': "<a href='{}' target='_blank'>{}</a>".format(bug.web_link, bug.status), 'description': bug.title})
    return formatted

def print_as_influxdb(bug_tasks):
    if bug_tasks:
        for bug_task in bug_tasks:
            print("bugs,tags={},id={} link=\"{}\",title=\"{}\",status=\"{}\"".format(
                bug_task.bug.tags,
                bug_task.bug.id,
                bug_task.web_link,
                bug_task.bug.title,
                bug_task.status))
def main():

    parser = argparse.ArgumentParser(
        description="Print launchpad bugs as influxdb lines")

    parser.add_argument('--tags', nargs='+', default=[])
    parser.add_argument('--status')
    args = parser.parse_args()

    print_as_influxdb(get_bugs(args.tags, args.status))

if __name__ == '__main__':
    main()
