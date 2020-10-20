import json
import os
import unittest

import mock
from telegraf_py3 import gerrit_changes


class TestGerritChanges(unittest.TestCase):

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

    def test_gerrit_changes_with_invalid_project(self):
        self.project = "test-project"
        obtained = gerrit_changes.get_gerrit_data(self.host, self.project)
        expected = []
        assert (expected == obtained)

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
    def test_negative_scenario(self, mock_get):
        mock_resp = self._mock_response(json_data='')
        mock_get.return_value = mock_resp
        gerrit_changes.get_gerrit_data(
                self.host, self.project, self.pages)

        self.assertRaises(
            json.decoder.JSONDecodeError,
            msg="json.decoder.JSONDecodeError: "
            "Expecting value: line 1 column 1 (char 0)")
