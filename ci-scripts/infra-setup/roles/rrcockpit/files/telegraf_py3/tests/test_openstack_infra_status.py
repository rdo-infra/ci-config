#!/usr/bin/env python
# pylint: disable=C0413

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openstack_infra_status  # noqa
import pandas as pd  # noqa


class TestOpenstackInfraStatus(unittest.TestCase):

    def setUp(self):
        # As data/issues are changing time to time, need to fetch them
        # first for testing.
        self.expected_issues = openstack_infra_status.get_infra_issues()
        self.expected_influxdb_lines = (
            openstack_infra_status.convert_to_influxdb_lines(
                self.expected_issues))

    def test_openstack_infra_status(self):
        result = openstack_infra_status.get_infra_issues()
        assert (self.expected_issues.iat[0, 0] == result.iat[0, 0])

    def test_convert_to_influxdb_lines(self):
        obtained = openstack_infra_status.convert_to_influxdb_lines(
            self.expected_issues)
        assert (self.expected_influxdb_lines == obtained)

    def test_convert_empty_data_to_influxdb_lines(self):
        # Expecting empty string for passing empty DataFrame to influxdb_lines
        self.expected_issues = pd.DataFrame()
        obtained = openstack_infra_status.convert_to_influxdb_lines(
            self.expected_issues)
        assert (obtained == '')
