import os, stat
import unittest
import time
from io import StringIO


from unittest.mock import patch, mock_open
from telegraf_py3 import rdocloud


class TestRDOCloud(unittest.TestCase):

    def setUp(self):
        self.servers = {
            'ACTIVE': 2, 'BUILD': 5, 'ERROR': 3, 'DELETED': 0,
            'undercloud': 1, 'multinode': 1, 'bmc': 0,
            'ovb-node': 0, 'other': 9, 'total': 11}
        self.quotes = {'cores': 7, 'instances': 3, 'ram': 14336, 'gbs': 205}
        self.stacks = {}
        self.fips = 1
        self.ports_down = 0
        self.ts = time.time()

    def test_compose_influxdb_data(self):
        obtained = rdocloud.compose_influxdb_data(
            self.servers, self.quotes, self.stacks, self.fips,
            self.ports_down, self.ts)
        self.assertIn('rdocloud-servers', obtained)
        self.assertIn('instances', obtained)

    def test_write_influxdb_file(self):
        fake_file_path = "/tmp"
        content = "Message to write on file to be written"
        with patch('telegraf_py3.rdocloud.open', mock_open()) as mocked_file:
            rdocloud.write_influxdb_file(fake_file_path, content)

            # assert if opened file on write mode 'w'
            mocked_file.assert_called_once_with(fake_file_path + '/influxdb_stats', 'w')

            # assert if write(content) was called from the file opened
            # in another words, assert if the specific content was written in file
            mocked_file().write.assert_called_once_with(content)

    def test_invalid_influxdb_data(self):
        expected = [None, '']
        obtained = rdocloud.compose_influxdb_data(None, None, None,
        None, None, self.ts)
        assert(obtained in expected)
