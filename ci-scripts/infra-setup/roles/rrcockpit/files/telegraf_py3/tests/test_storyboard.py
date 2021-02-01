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

    def test_get_storyboard_data(self):
        result = storyboard.get_storyboard_data(
            self.host, self.project_id, self.story_status, self.limit)
        self.assertIsNotNone(result)
        self.assertEqual(self, self.data, result)
        
