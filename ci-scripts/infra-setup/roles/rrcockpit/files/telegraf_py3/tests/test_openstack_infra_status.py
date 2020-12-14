import datetime
import os
import sys
import unittest

myPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, myPath + '/../')

import pandas as pd
from telegraf_py3 import openstack_infra_status


class TestOpenstackInfraStatus(unittest.TestCase):

    def setUp(self):
        issues = [
            'restarted gerritbot as it switched irc servers at 16:55 and never came back'
        ]
        times = [datetime.datetime(2020, 12, 30, 21, 28, 20)]

        self.time_and_issue = pd.DataFrame({'time': times, 'issue': issues})
        self.time_and_issue = self.time_and_issue.set_index('time')
        print(self.time_and_issue)

    def test_openstack_infra_status(self):
        result = openstack_infra_status.get_infra_issues()
        assert (self.time_and_issue.iat[0, 0] == result.iat[0, 0])

    def test_convert_to_influxdb_lines(self):
        expected = 'openstack-infra-issues issue="b"issued \'poweroff\' on 77.81.189.96 (was mirror01.sto2.citycloud.openstack.org) since that region is not in use and the host is not under config management"" 1609343900000000000\n'
        obtained = openstack_infra_status.convert_to_influxdb_lines(self.time_and_issue)
        assert (expected == obtained)