#!/usr/bin/env python
# pylint: disable=C0413

import json
import os
import sys
import unittest

import mock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import get_jenkins_jobs  # noqa


class TestJenkinsJobs(unittest.TestCase):

    def setUp(self):
        self.jenkins_jobs = []
        full_path = os.path.dirname(os.path.abspath(__file__))
        with open(full_path + '/data/jenkins-test-jobs', 'r') as f:
            for line in f:
                row = json.loads(line)
                self.jenkins_jobs.append(row)
            f.close()
        self.jenkins_url = "https://jenkins-cloudsig-ci.apps.ocp.ci.centos.org/"
        self.release = "master"
        self.name_filter = "tripleo-quickstart"
        self.response = None

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
    def test_request_data(self, mock_get):
        mock_resp = self._mock_response(json_data=str(self.jenkins_jobs))
        mock_get.return_value = mock_resp
        response = get_jenkins_jobs.request_data(self.jenkins_url)
        self.assertEqual(200, response.status_code)

    def test_request_data_with_invalid_url(self):
        self.assertRaises(
            Exception, get_jenkins_jobs.request_data, "https://test.org/")

    def test_latest_jenkins_job(self):
        job_with_build_id = {}
        imported_jobs = self.jenkins_jobs
        for i in imported_jobs:
            job_with_build_id[i['build_id']] = i
        latest_job_build = max(list(job_with_build_id.keys()))
        self.assertEqual(latest_job_build, imported_jobs[0]['build_id'])
