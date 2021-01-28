#!/usr/bin/env python
# pylint: disable=C0413

import io
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import get_jenkins_jobs  # noqa


class TestJenkinsJobs(unittest.TestCase):

    def setUp(self):
        self.jenkins_url = "https://ci.centos.org/"
        self.release = "master"
        self.name_filter = "tripleo-quickstart"
        self.response = None

    def test_request_data(self):
        response = get_jenkins_jobs.request_data(self.jenkins_url)
        # check for status code 200 to verify response is OK
        self.assertEqual(200, response.status_code)

    def test_print_data(self):
        capturedOutput = io.StringIO()
        sys.stdout = capturedOutput
        get_jenkins_jobs.print_data(get_jenkins_jobs.request_data(
            self.jenkins_url), self.release, self.name_filter)
        sys.stdout = sys.stdout
        print('Captured', capturedOutput.getvalue())

    def test_request_data_with_invalid_url(self):
        self.assertRaises(
            Exception, get_jenkins_jobs.request_data, "https://test.org/")
