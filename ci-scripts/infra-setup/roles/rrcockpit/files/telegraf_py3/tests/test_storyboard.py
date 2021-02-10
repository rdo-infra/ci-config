import json
import os
import unittest

import mock
from telegraf_py3 import storyboard


class TestStoryBoard(unittest.TestCase):

    def setUp(self):
        full_path = os.path.dirname(os.path.abspath(__file__))
        with open(full_path + '/data/storyboard-test-data.json') as f:
            self.data = json.load(f)
        self.host = 'https://storyboard.openstack.org'
        self.project_id = 1164
        self.story_status = 'active'
        self.limit = 100

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
    def test_get_storyboard_data(self, mock_get):
        mock_resp = self._mock_response(json_data=self.data)
        mock_get.return_value = mock_resp
        result = storyboard.get_storyboard_data(
            self.host, self.project_id, self.story_status, self.limit)
        self.assertIsNotNone(result)
        assert (self.data == result)

    def test_invalid_storyboard_data(self):
        self.project_id = 0000
        self.story_status = 'inactive'
        expected = [None, []]
        result = storyboard.get_storyboard_data(
            self.host, self.project_id, self.story_status, self.limit)
        assert(result in expected)

    def test_extract_story(self):
        story = self.data[0]
        result = storyboard.extract_story(story, self.host)
        self.assertIsNotNone(result)
