import os
import unittest
from datetime import datetime
from unittest import mock
from unittest.mock import patch

import ruck_rover


class TestRuckRover(unittest.TestCase):

    def test_date_diff_in_seconds(self):
        date1 = datetime(2020, 5, 17)
        date2 = datetime(2020, 5, 18)
        self.assertEqual(
            ruck_rover.date_diff_in_seconds(date2, date1), 86400)

    def test_dhms_from_seconds(self):
        self.assertEqual(
            ruck_rover.dhms_from_seconds(0), (0, 0, 0))
        self.assertEqual(
            ruck_rover.dhms_from_seconds(5402), (1, 30, 2))

    def test_strip_date_time_from_string(self):
        input_string = "2021-05-31 13:06:07.428188 | Job console starting..."
        self.assertEqual(
            ruck_rover.strip_date_time_from_string(
                input_string), "2021-05-31 13:06:07")

    def test_convert_string_date_object(self):
        input_date = '2021-05-31 13:06:07'
        expected_output = datetime(2021, 5, 31, 13, 6, 7)
        self.assertEqual(
            ruck_rover.convert_string_date_object(
                input_date), expected_output)

    def test_delete_file(self):
        with patch('os.remove'):
            ruck_rover.delete_file('foo')

    @patch('ruck_rover.delete_file')
    @patch('ruck_rover.download_file')
    def test_find_job_run_time(self, m_download, m_delete):
        full_path = os.path.dirname(os.path.abspath(__file__))
        # to-do correct path when move test file to correct place
        m_download.return_value = full_path + "/data/job-output.txt"
        m_delete.return_value = None
        expected = "1 hr 32 mins 34 secs"
        obtained = ruck_rover.find_job_run_time('www.demoourl.com')
        self.assertEqual(expected, obtained)

    @patch('ruck_rover.delete_file')
    @patch('ruck_rover.download_file')
    def test_find_failure_reason(self, m_download, m_delete):
        full_path = os.path.dirname(os.path.abspath(__file__))
        # to-do correct path when move test file to correct place
        m_download.return_value = full_path + "/data/failures_file"
        m_delete.return_value = None
        expected = "Tempest tests failed."
        obtained = ruck_rover.find_failure_reason('www.demoourl.com')
        self.assertEqual(expected, obtained)

    @patch('ruck_rover.requests.get')
    def test_web_scrape(self, m_get):
        full_path = os.path.dirname(os.path.abspath(__file__))
        with open(full_path + "/data/master.yaml") as file:
            data = file.read()
        m_get.return_value.text = data
        obtained = ruck_rover.web_scrape('www.demooourl.com')
        self.assertEqual(data, obtained)

    @patch('ruck_rover.requests.get')
    def test_url_response_in_yaml(self, m_get):
        full_path = os.path.dirname(os.path.abspath(__file__))
        with open(full_path + "/data/master.yaml") as file:
            data = file.read()
        m_get.return_value.text = data
        obtained = ruck_rover.url_response_in_yaml('www.demooourl.com')
        self.assertTrue(isinstance(obtained, dict))
        self.assertEqual('master', obtained['release'])

    @patch('ruck_rover.requests.get')
    def test_gather_basic_info_from_criteria(self, m_get):
        full_path = os.path.dirname(os.path.abspath(__file__))
        with open(full_path + "/data/master.yaml") as file:
            data = file.read()
        m_get.return_value.text = data
        a_url = 'https://trunk.rdoproject.org/api-centos8-master-uc'
        b_url = 'https://trunk.rdoproject.org/centos8-master/'
        expected = (a_url, b_url)
        obtained = ruck_rover.gather_basic_info_from_criteria(
            'www.demooourl.com')
        self.assertEqual(obtained, expected)

    def test_find_jobs_in_integration_criteria(self):
        yaml_data = {
            'release': 'master',
            'promotions': {
                'current-tripleo': {
                    'candidate_label': 'tripleo-ci-testing',
                    'criteria': [
                        'periodic-tripleo-ci-build-containers-ubi-8-push',
                        'periodic-tripleo-centos-8-buildimage-overcloud-full']
                            }}}
        with patch('ruck_rover.url_response_in_yaml') as m_get:
            m_get.return_value = yaml_data
            obtained = ruck_rover.find_jobs_in_integration_criteria(
                            'www.demoourl.com')
            expected = [
                'periodic-tripleo-ci-build-containers-ubi-8-push',
                'periodic-tripleo-centos-8-buildimage-overcloud-full']
            self.assertEqual(
                expected, obtained)

    def test_find_jobs_in_component_criteria(self):
        yaml_data = {
            'promoted-components': {
                'baremetal': [
                    'periodic-tripleo-baremetal-master',
                    'periodic-tripleo-sc012-baremetal-master'],
                'cinder': [
                    'periodic-tripleo-cinder-master',
                    'periodic-tripleo-sc01-cinder-master']
                        }}
        with patch('ruck_rover.url_response_in_yaml') as m_get:
            m_get.return_value = yaml_data
            obtained = ruck_rover.find_jobs_in_component_criteria(
                            'www.demoourl.com', 'baremetal')
            expected = [
                'periodic-tripleo-baremetal-master',
                'periodic-tripleo-sc012-baremetal-master']
            self.assertEqual(
                expected, obtained)

            with self.assertRaises(KeyError):
                ruck_rover.find_jobs_in_component_criteria(
                    'www.demoourl.com', 'xyz')

    def test_fetch_hashes_from_commit_yaml(self):
        yaml_data = {
            'commits': [{
                'commit_hash': 'c6',
                'distro_hash': '03',
                'extended_hash': 'None'}]}
        with patch('ruck_rover.url_response_in_yaml') as m_get:
            m_get.return_value = yaml_data
            obtained = ruck_rover.fetch_hashes_from_commit_yaml(
                            'www.demoourl.com')
            expected = ('c6', '03', 'None')
            self.assertEqual(expected, obtained)

    def test_load_conf_file(self):
        full_path = os.path.dirname(os.path.abspath(__file__))
        my_file = full_path + '/data/test_conf_ruck_rover.yaml'
        obtained = ruck_rover.load_conf_file(my_file, "upstream")
        expected = {'upstream': {'zuul_url': 'abc',
                                 'dlrnapi_url': 'def',
                                 'promoter_url': 'ghi',
                                 'git_url': 'jkl'}}
        self.assertEqual(expected, obtained)


class TestRuckRoverWithCommonSetup(unittest.TestCase):
    def setUp(self):
        full_path = os.path.dirname(os.path.abspath(__file__))
        my_file = '/data/integration_promotion.json'
        with open(full_path + my_file, encoding='utf-8') as f:
            self.data = f.read()
        self.url = 'http://zuul.openstack.org/api/builds'
        self.pages = 1
        self.offset = 0

    def _mock_response(
            self,
            status=200,
            content="CONTENT",
            json_data=None,
            text=None,
            raise_for_status=None):
        mock_resp = mock.Mock()
        # mock raise_for_status call w/optional error
        mock_resp.raise_for_status = mock.Mock()
        if raise_for_status:
            mock_resp.raise_for_status.side_effect = raise_for_status
        # set status code and content
        mock_resp.status_code = status
        mock_resp.text = text
        # add json data if provided
        if json_data:
            mock_resp.json = mock.Mock(
                return_value=json_data
            )
        return mock_resp

    @mock.patch('requests.get')
    def test_get_job_history(self, mock_get):
        mock_resp = self._mock_response(text=self.data, raise_for_status=None)
        mock_get.return_value = mock_resp
        job = "periodic-tripleo-ci-centos-8-standalone-master"
        zb_periodic = "https://review.rdoproject.org/zuul/api/builds"
        history = ruck_rover.get_job_history(job, zb_periodic)
        self.assertIn(job, history.keys())
        self.assertEqual(history[job]['SUCCESS'], 3)
        self.assertEqual(history[job]['FAILURE'], 2)
        self.assertEqual(history[job]['OTHER'], 0)


if __name__ == '__main__':
    unittest.main()
