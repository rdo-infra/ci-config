import time
import unittest
from unittest.mock import mock_open, patch

from telegraf_py3 import vexxhost


class TestVexxHost(unittest.TestCase):

    def setUp(self):
        self.servers = {
            'ACTIVE': 141, 'BUILD': 0, 'ERROR': 0, 'DELETED': 0,
            'undercloud': 71, 'multinode': 0, 'bmc': 22,
            'ovb-node': 57, 'other': 6, 'total': 156}
        self.quotes = {
            'cores': 824, 'instances': 156, 'ram': 1105920, 'gbs': 0}
        self.stacks = {
            'stacks_total': 22, 'create_complete': 22, 'create_failed': 0,
            'create_in_progress': 0, 'delete_in_progress': 0,
            'delete_failed': 0, 'delete_complete': 0, 'old_stacks': 0}
        self.fips = 1
        self.ports_down = 0
        self.ts = time.time()

    def test_compose_influxdb_data(self):
        obtained = vexxhost.compose_influxdb_data(
            self.servers, self.quotes, self.stacks, self.fips,
            self.ports_down, self.ts)
        self.assertIn('vexxhost-servers', obtained)
        self.assertIn('instances', obtained)

    def test_write_influxdb_file(self):
        fake_file_path = "/tmp"
        content = "Message to write on file to be written"
        with patch('telegraf_py3.vexxhost.open', mock_open()) as mocked_file:
            vexxhost.write_influxdb_file(fake_file_path, content)

            # assert if opened file on write mode 'w'
            mocked_file.assert_called_once_with(
                fake_file_path + '/influxdb_stats_vexx', 'w')

            # assert if write(content) was called from the file opened
            # in another words, assert if the specific content was
            # written in file
            mocked_file().write.assert_called_once_with(content)

    def test_invalid_influxdb_data(self):
        expected = [None, '']
        obtained = vexxhost.compose_influxdb_data(
                None, None, None, None, None, self.ts)
        assert(obtained in expected)
