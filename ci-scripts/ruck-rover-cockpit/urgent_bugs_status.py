#!/bin/env python
import requests
import re
import json
import os

from launchpadlib.launchpad import Launchpad

cachedir = "{}/.launchpadlib/cache/".format(os.path.expanduser('~'))

def get_urgent_bugs():
    launchpad = Launchpad.login_anonymously('OOOQ Ruck Rover', 'production', cachedir, version='devel')
    project = launchpad.projects['tripleo']

    # We can filter by status too
    bugs = project.searchTasks(tags='alert')
    return bugs

def format_bugs(bugs):
    formatted = []
    for bug in bugs:
        formatted.append({'link': "<a href='{}' target='_blank'>{}</a>".format(bug.web_link, bug.status), 'description': bug.title})
    return formatted

def print_as_influxdb(bug_tasks):
    if bug_tasks:
        for bug_task in bug_tasks:
            print("urgent-bugs,id={} link=\"{}\",title=\"{}\",status=\"{}\"".format(
                bug_task.bug.id,
                bug_task.web_link,
                bug_task.bug.title,
                bug_task.status))
    else:
        print('urgent-bugs status="no bugs"')
def main():

    print_as_influxdb(get_urgent_bugs())

if __name__ == '__main__':
    main()
