import unittest
from unittest.mock import patch
import ruck_rover


class TestRuckRover(unittest.TestCase):

    def test_web_scrap(self):
        data = """---
        release: master
        dry_run: no
        promoted-components:
          baremetal:
            - periodic-tripleo-ci-centos-8-standalone-baremetal-master
        """
        with patch('ruck_rover.requests.get') as m_get:
            m_get.return_value.text = data
            obtained = ruck_rover.web_scrap('www.demooourl.com')
            self.assertIn(data, obtained)

    def test_url_response_in_yaml(self):
        data = """---
        release: master
        dry_run: no
        promoted-components:
          baremetal:
            - periodic-tripleo-ci-centos-8-standalone-baremetal-master
        """
        with patch('ruck_rover.web_scrap') as m_get:
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


if __name__ == '__main__':
    unittest.main()
