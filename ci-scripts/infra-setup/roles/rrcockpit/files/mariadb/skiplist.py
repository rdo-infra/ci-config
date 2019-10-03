#!/usr/bin/env python3
# Copyright 2019 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import tempest_file_downloader
import tempest_html_json
import glob
import os
import json


parse_result = []
previously_processed_files = [
    'tempest.master.html',
    'tempest.stein.html']
recent_files = []


def get_diff():
    """
    This function gives the difference of previously proccessed files and
    recent files
    """
    list_of_files = glob.glob('/tmp/skip/*.html')
    recent_files = max(list_of_files, key=os.path.getctime)
    return list(set(previously_processed_files) - set(recent_files))


def get_files():
    """
    This function gives the result of all the files parsed from html to json
    """
    tempest_file_downloader.get_last_build()
    previously_processed_files.extend(get_diff())
    for file in get_diff():
        parse_result.append(tempest_html_json.main())
    return parse_result


def get_output_file():
    json.dumps(get_files(), sort_keys=True, indent=2)


def print_as_csv():
    for file in get_files():
        for result in file.values():
            for release_name, test in result.iteritems():
                for testname, status in test.iteritems():
                    print(('{},{},{}').format(release_name, testname, status))


if __name__ == "__main__":
    print_as_csv()
