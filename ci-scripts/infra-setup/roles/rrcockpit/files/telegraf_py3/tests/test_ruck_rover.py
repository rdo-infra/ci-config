import os
import unittest
from unittest import mock
from unittest.mock import patch

import ruck_rover


class TestRuckRover(unittest.TestCase):
    def test_web_scrape(self):
        data = """---
        release: master
        dry_run: no
        promoted-components:
          baremetal:
            - periodic-tripleo-ci-centos-8-standalone-baremetal-master
        """
        with patch('ruck_rover.requests.get') as m_get:
            m_get.return_value.text = data
            obtained = ruck_rover.web_scrape('www.demooourl.com')
            self.assertIn(data, obtained)

    def test_url_response_in_yaml(self):
        data = """---
        release: master
        dry_run: no
        promoted-components:
          baremetal:
            - periodic-tripleo-ci-centos-8-standalone-baremetal-master
        """
        with patch('ruck_rover.web_scrape') as m_get:
            m_get.return_value = data
            obtained = ruck_rover.url_response_in_yaml('www.demooourl.com')
            self.assertIn('release', obtained)

    def test_gather_basic_info_from_criteria(self):
        yaml_data = {
            'release': 'master',
            'api_url': 'https://trunk.rdoproject.org/api-centos8-master-uc',
            'base_url': 'https://trunk.rdoproject.org/centos8-master/',
        }
        with patch('ruck_rover.url_response_in_yaml') as m_get:
            m_get.return_value = yaml_data
            a_url, b_url = ruck_rover.gather_basic_info_from_criteria(
                            'www.demoourl.com')
            self.assertEqual(
                a_url, 'https://trunk.rdoproject.org/api-centos8-master-uc')
            self.assertEqual(
                b_url, 'https://trunk.rdoproject.org/centos8-master/')

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
        ZB_RDO = "https://review.rdoproject.org/zuul/api/builds"
        history = ruck_rover.get_job_history(job, ZB_RDO)
        self.assertIn(job, history.keys())
        self.assertEqual(history[job]['SUCCESS'], 3)
        self.assertEqual(history[job]['FAILURE'], 2)
        self.assertEqual(history[job]['OTHER'], 0)


if __name__ == '__main__':
    unittest.main()
