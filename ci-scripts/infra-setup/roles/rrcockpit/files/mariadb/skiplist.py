#!/usr/bin/env python
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

import json
import tempest_file_downloader
import tempest_html_json

from datetime import datetime


parse_result = []


def get_files():
    """
    This function gives the result of all the files parsed
    """
    release_names = ['master', 'train', 'stein', 'rocky', 'queens']
    for release_name in release_names:
        if release_name in ['master', 'train']:
            file_name = "stestr_results.html"
        else:
            file_name = "tempest.html.gz"
        try:
            log_url, release = tempest_file_downloader.get_last_build(
                    "periodic-tripleo-ci-centos-7-ovb-1ctlr_2comp-"
                    "featureset021-" + release_name, file_name)
            global log
            log = log_url
        except Exception:
            continue
        parse_result.append(tempest_html_json.output(log, release))
    return parse_result


def get_output_file():
    """
    This function returns json serialized data
    """
    json.dumps(get_files(), sort_keys=True, indent=2)


def print_as_csv():
    """
    This function print the result in csv format
    """
    timestamp = datetime.now()
    for file in get_files():
        for result in file.values():
            for release_name, test in result.items():
                for testname, status in test.items():
                    print(('{},{},{},{},{}').format(
                        0,
                        release_name,
                        testname.split('(')[-1].replace("']", ""),
                        str(timestamp),
                        status))


if __name__ == "__main__":
    print_as_csv()
