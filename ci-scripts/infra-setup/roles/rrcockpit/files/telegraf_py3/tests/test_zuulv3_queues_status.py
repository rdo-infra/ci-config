import json
import os
import unittest

import mock
from telegraf_py3 import zuulv3_queues_status


class TestZuulV3QueueStatus(unittest.TestCase):

    def setUp(self):
        full_path = os.path.dirname(os.path.abspath(__file__))
        with open(full_path + '/data/zuulv3_queues_data') as f:
            self.data = json.load(f)

        self.url = 'http://zuul.openstack.org/api/status'
        self.pipeline = 'gate'
        self.queue_name = 'tripleo'
        self.project_regex = '.*tripleo.*'

    def _mock_response(
            self,
            status=200,
            content="CONTENT",
            json_data=None,
            raise_for_status=None):
        mock_resp = mock.Mock()
        # mock raise_for_status call w/optional error
        mock_resp.raise_for_status = mock.Mock()
        if raise_for_status:
            mock_resp.raise_for_status.side_effect = raise_for_status
        # set status code and content
        mock_resp.status_code = status
        mock_resp.content = content
        # add json data if provided
        if json_data:
            mock_resp.json = mock.Mock(
                return_value=json_data
            )
        return mock_resp

    @mock.patch('requests.get')
    def test_find_zuul_queues(self, mock_get):
        mock_resp = self._mock_response(content=str(self.data))
        mock_get.return_value = mock_resp
        result = zuulv3_queues_status.find_zuul_queues(
            self.url, self.pipeline, self.queue_name, self.project_regex)
        expected_keys = set().union(*(d.keys() for d in self.data))
        actual_keys = set().union(*(d.keys() for d in result))
        self.assertEqual(expected_keys, actual_keys)
        self.assertIsNotNone(result)

    def test_calculate_minutes_enqueued(self):
        enqueue_time = 1613028228218
        obtained_time = zuulv3_queues_status.calculate_minutes_enqueued(
            enqueue_time)
        self.assertIsNot(0, obtained_time)
