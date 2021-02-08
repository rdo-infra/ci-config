import json
import os
import unittest

import mock
from telegraf_py3 import zuulv3_job_builds


class TestStoryBoard(unittest.TestCase):

    def setUp(self):
        full_path = os.path.dirname(os.path.abspath(__file__))
        with open(full_path + '/data/zuulv3_job_builds_test_data') as f:
            self.data = json.load(f)

        self.url = 'http://zuul.openstack.org/api/'
        self.query = {'project': 'openstack/puppet-tripleo'}
        self.pages = 1
        self.offset = 0

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
    def test_get_builds_info(self, mock_get):
        mock_resp = self._mock_response(json_data=self.data)
        mock_get.return_value = mock_resp
        result = zuulv3_job_builds.get_builds_info(
            self.url, self.query, self.pages, self.offset)
        self.assertIsNotNone(result)
        assert (self.data == result)

    def test_invalid_url_builds_data(self):
        expected = []
        self.url = 'http://zuul.test.org/api/'
        result = zuulv3_job_builds.get_builds_info(
            self.url, self.query, self.pages, self.offset)
        assert (expected == result)

    def test_influx(self):
        result = zuulv3_job_builds.influx(self.data[0])
        self.assertIsNotNone(result)
