import json
import os
import unittest

from telegraf_py3 import gerrit_changes


class TestDiffTripleOBuilds(unittest.TestCase):

    def setUp(self):
        full_path = os.path.dirname(os.path.abspath(__file__))
        with open(full_path + '/data/gerrit-test-data.json') as f:
            self.data = json.load(f)
        self.host = 'https://review.opendev.org'
        self.project = 'openstack/ansible-collections-openstack'
        self.pages = 1

    def test_gerrit_changes(self):
        obtained = gerrit_changes.get_gerrit_data(
                self.host, self.project, self.pages)
        expected_keys = set().union(*(d.keys() for d in self.data))
        actual_keys = set().union(*(d.keys() for d in obtained))

        assert (expected_keys == actual_keys)
        assert (self.data[0]['project'] == obtained[0]['project'])
