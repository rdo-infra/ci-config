import json
from os import path
from bs4 import BeautifulSoup

file_name = "tempest"
pass_test_cases = []
fail_test_cases = []
Pass_test_cases_names = []
Fail_test_cases_names = []
Fail = []
Pass = []

def parse_html():
    """
    This function parses the html data in python lists.
    """
    global pass_test_cases, fail_test_cases
    if path.exists(file_name):
        with open("tempest") as fp:
            soup = BeautifulSoup(fp, "html.parser")
        pass_test_cases = soup.find_all('tr', class_ = "passClass")
        fail_test_cases = soup.find_all('tr', class_ = "failClass")
    else:
        raise Exception("File doesn't exist on the given path")

def get_pass_tests_name():
    """
    This function retrieves pass test names from python object and dumps the
    result in json.
    """
    for test in pass_test_cases:
        td_pass_test_name = test.find_all('td', class_ = "testname")
        for name in td_pass_test_name:
            Pass_test_cases_names.append(name.text)
        pass_result = json.dumps(Pass_test_cases_names)
    return pass_result
    
def get_fail_tests_name():
    """
    This function retrieves fail test names from python object and dumps the
    result in json.
    """
    for test in fail_test_cases:
        td_fail_test_name = test.find_all('td', class_ = "testname")
        for name in td_fail_test_name:
            Fail_test_cases_names.append(name.text)
        fail_result = json.dumps(Fail_test_cases_names)
    return fail_result

def get_status_fail():
    """
    This function retrieves status of fail test cases
    """
    for status in fail_test_cases:
        Fail.append("Fail")
    fail_status_result = json.dumps(Fail)
    return fail_status_result

def get_status_pass():
    """
    This function retrieves status of pass test cases
    """
    for status in pass_test_cases:
        Pass.append("Pass")
    pass_status_result = json.dumps(Pass)
    return pass_status_result

parse_html()
print(get_pass_tests_name())
print(get_fail_tests_name())
print(get_status_fail())
print(get_status_pass())