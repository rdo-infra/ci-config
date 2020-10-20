import json
import os
import unittest

import gerrit_changes


class TestDiffTripleOBuilds(unittest.TestCase):

    def setUp(self):
        with open('test-data.json') as f:
            self.data = json.load(f)

    def test_gerrit_changes(self):
        host = 'https://review.opendev.org'
        project = 'openstack/ansible-collections-openstack'
        pages = 1

        obtained = gerrit_changes.get_gerrit_data(host, project, pages)

        assert (self.data[0]['project'] == obtained[0]['project'])

