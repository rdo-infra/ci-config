import os
import sys
import datetime
import pandas as pd
import unittest

from telegraf_py3 import openstack_infra_status

class TestOpenstackInfraStatus(unittest.TestCase):

    def setUp(self):
        issues = ['zuul restarted to pickup https://review.opendev.org/c/zuul/zuul/+/711002']

        times = [datetime.datetime(2020, 12, 16, 5, 7, 46)]

        self.time_and_issue = pd.DataFrame({'time': times, 'issue': issues})
        self.time_and_issue = self.time_and_issue.set_index('time')
        print(self.time_and_issue)


    def test_openstack_infra_status(self):
        self.result = openstack_infra_status.get_infra_issues()
        assert (self.time_and_issue.iat[0, 0] == self.result.iat[0, 0])
