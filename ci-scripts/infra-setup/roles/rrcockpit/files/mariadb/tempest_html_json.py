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
import re
from bs4 import BeautifulSoup
from os import path


result = {"Release": {
             "master": {"Testname": "Status"},
             "stein": {"Testname": "Status"},
             "rocky": {"Testname": "Status"},
             "queens": {"Testname": "Status"}
        }}
releases = ["master", "stein", "rocky", "queens"]


def parse_html():
    """
    This function parses the html data in python lists.
    """
    pass_test_cases = []
    fail_test_cases = []
    if path.exists("tempest"):
        with open("tempest") as fp:
            soup = BeautifulSoup(fp, "html.parser")
        pass_test_cases = soup.find_all('tr', class_="passClass")
        fail_test_cases = soup.find_all('tr', class_="failClass")
    else:
        raise Exception("File doesn't exist on the given path")
    return (pass_test_cases, fail_test_cases)


def get_pass_tests_name():
    """
    This function retrieves pass test names from python object and dumps the
    result in json.
    """
    pass_test_cases, fail_test_cases = parse_html()
    pass_test_cases_names = []
    for test in pass_test_cases:
        td_pass_test_name = test.find_all('td', class_="testname")
        for name in td_pass_test_name:
            filter = re.search("setUpClass ", name.text)
            if filter:
                pass_test_cases_names.append(
                        re.split("setUpClass ", name.text))
            else:
                pass_test_cases_names.append(name.text)
    return pass_test_cases_names


def get_fail_tests_name():
    """
    This function retrieves fail test names from python object and dumps the
    result in json.
    """
    pass_test_cases, fail_test_cases = parse_html()
    fail_test_cases_names = []
    for test in fail_test_cases:
        td_fail_test_name = test.find_all('td', class_="testname")
        for name in td_fail_test_name:
            fail_test_cases_names.append(name.text)
    return fail_test_cases_names


def get_status_fail():
    """
    This function retrieves status of fail test cases
    """
    pass_test_cases, fail_test_cases = parse_html()
    fail_result = []
    for status in fail_test_cases:
        fail_result.append("Fail")
    return fail_result


def get_status_pass():
    """
    This function retrieves status of pass test cases
    """
    pass_test_cases, fail_test_cases = parse_html()
    pass_result = []
    for status in pass_test_cases:
        pass_result.append("Pass")
    return pass_result


def combine_status():
    """
    This function combines the status of failed and passed testcases
    """
    pass_result = get_status_pass()
    fail_result = get_status_fail()
    return pass_result + fail_result


def combine_testcases():
    """
    This function combines the failed and passed testcases names
    """
    pass_test_cases_names = get_pass_tests_name()
    fail_test_cases_names = get_fail_tests_name()
    return pass_test_cases_names + fail_test_cases_names


def get_result_dict():
    """
    This function returns the json serialized dictionary of testcase name and
    status of the test case in json
    """
    combine = zip(combine_testcases(), combine_status())
    test_status = {str(x): str(y) for x, y in combine}
    for i in releases:
        if i in result['Release'].keys():
            result['Release']['rocky'] = test_status
            break
    return result


def main():

    return get_result_dict()
