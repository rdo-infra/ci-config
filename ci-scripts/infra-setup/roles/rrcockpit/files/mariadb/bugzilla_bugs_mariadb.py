#!/usr/bin/env python
from __future__ import print_function
import sys

import bugzilla

URL = "https://bugzilla.redhat.com"


# pylint: disable=undefined-variable
api_key = "B5ryD1LwjmAE1ZMhRQGsSBMszyBqnqMq9UpDigxc"
# pylint: enable=undefined-variable

# Login
bzapi = bugzilla.Bugzilla(URL, api_key=api_key)
assert bzapi.logged_in


bug_query1 = bzapi.url_to_query(
    "https://bugzilla.redhat.com/buglist.cgi?bug_"
    "status=NEW&bug_status=ASSIGNED&bug_status=POST&bug_status=MODIFIED&bug_"
    "status=ON_DEV&bug_status=ON_QA&bug_status=RELEASE_PENDING"
    "&chfield=%5BBug%20creation%5D&chfieldto=-9d&columnlist=product%2Ccomponent"
    "%2Ctarget_release%2Cassigned_to%2Cbug_status%2Cresolution%2Cshort_desc%"
    "2Cchangeddate&f1=product&f10=flagtypes.name&"
    "f11=CP&f12=flagtypes.name&f2=cf_internal_whiteboard&f3=component&f4="
    "cf_conditional_nak&f5=cf_qe_conditional_nak&f6=OP&f7=keywords&f8=priority&"
    "f9=bug_severity&keywords=FutureFeature%2C%20Tracking%2C%20Documentation%"
    "2C%20&keywords_type=nowords&list_id=10123136&o1=equals&o10=substring&o12"
    "=notsubstring&o2=substring&o3=notsubstring&o4=isempty&o5=isempty&o7="
    "substring&o8=notsubstring&o9=notsubstring&query_format=advanced&v1="
    "Red%20Hat%20OpenStack&v10=rhos&v12=needinfo&v2"
    "=DFG%3APCCI&v3=doc&v7=Triaged&v8=unspecified&v9=unspecified")


def get_bugs(query):
    query["include_fields"] = ["id", "status", "priority", "summary"]
    bugs = bzapi.query(query)
    return bugs


def print_as_csv(bugs):
    for bug in bugs:
        bug.weburl = bug.weburl.replace('"', '')
        print(('{},{},{},{},"{}"').format(
            bug.id,
            bug.status,
            bug.priority,
            bug.weburl,
            bug.summary))


def main():
    bugs = get_bugs(bug_query1)
    print_as_csv(bugs)


if __name__ == '__main__':
    main()
