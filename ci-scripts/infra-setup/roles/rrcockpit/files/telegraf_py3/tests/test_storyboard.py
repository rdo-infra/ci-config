import json
import os
import unittest

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

    def test_get_storyboard_data(self):
        result = storyboard.get_storyboard_data(
            self.host, self.project_id, self.story_status, self.limit)
        self.assertIsNotNone(result)
        assert (self.data == result)

    def test_invalid_storyboard_data(self):
        self.project_id = 0000
        self.story_status = 'inactive'
        expected = []
        result = storyboard.get_storyboard_data(
            self.host, self.project_id, self.story_status, self.limit)
        assert(expected == result)

    def test_extract_story(self):
        story = self.data[0]
        result = storyboard.extract_story(story, self.host)
        self.assertIsNotNone(result)
