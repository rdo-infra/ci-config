import json
import os
import unittest
from unittest import mock
from unittest.mock import call, patch

import ruck_rover


class TestRuckRover(unittest.TestCase):
    # pylint: disable=too-many-public-methods
    def setUp(self):
        self.maxDiff = None

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

    def test_find_jobs_in_integration_criteria(self):
        criteria = {
            'release': 'master',
            'promotions': {
                'current-tripleo': {
                    'candidate_label': 'tripleo-ci-testing',
                    'criteria': [
                        'periodic-tripleo-ci-build-containers-ubi-8-push',
                        'periodic-tripleo-centos-8-buildimage-overcloud-full']
                            }}}
        obtained = ruck_rover.find_jobs_in_integration_criteria(criteria)
        expected = set([
            'periodic-tripleo-ci-build-containers-ubi-8-push',
            'periodic-tripleo-centos-8-buildimage-overcloud-full'])
        self.assertEqual(
            expected, obtained)

    def test_find_jobs_in_component_criteria(self):
        criteria = {
            'promoted-components': {
                'baremetal': [
                    'periodic-tripleo-baremetal-master',
                    'periodic-tripleo-sc012-baremetal-master'],
                'cinder': [
                    'periodic-tripleo-cinder-master',
                    'periodic-tripleo-sc01-cinder-master']
                        }}
        obtained = ruck_rover.find_jobs_in_component_criteria(
            criteria, 'baremetal')
        expected = set([
            'periodic-tripleo-baremetal-master',
            'periodic-tripleo-sc012-baremetal-master'])
        self.assertEqual(
            expected, obtained)

        with self.assertRaises(KeyError):
            ruck_rover.find_jobs_in_component_criteria(
                criteria, 'xyz')

    def test_fetch_hashes_from_commit_yaml(self):
        criteria = {
            'commits': [{
                'commit_hash': 'c6',
                'distro_hash': '03',
                'extended_hash': 'None'}]}

        obtained = ruck_rover.fetch_hashes_from_commit_yaml(criteria)
        expected = ('c6', '03', None)
        self.assertEqual(expected, obtained)

    def test_get_diff_the_same(self):
        file_content = ["file1", ([], [0, 0, 0, 0, 0, 0, 0, 0, 0, "abc"], [])]
        output = ruck_rover.get_diff("", file_content, "", file_content)
        self.assertFalse(output)

    @patch("ruck_rover.Table.add_row")
    @patch("ruck_rover.Table.add_column")
    def test_get_diff_different(self, m_column, m_row):
        file1 = ["file1", ([], [0, 0, 0, 0, 0, 0, 0, 0, 0, "abc"], [])]
        file2 = ["file2", ([], [0, 0, 0, 0, 0, 0, 0, 0, 0, "xyz"], [])]
        ruck_rover.get_diff("Control", file1, "Test", file2)

        m_column.assert_has_calls([
            call("Control", style="dim", width=85),
            call("Test", style="dim", width=85)
        ])
        m_row.assert_called_with(str("abc"), str("xyz"))

    @mock.patch('requests.get')
    def test_get_csv_not_ok(self, m_get):
        m_response = mock.MagicMock(ok=False)
        m_get.return_value = m_response
        output = ruck_rover.get_csv("")
        self.assertIsNone(output)

    @mock.patch('csv.reader')
    @mock.patch('requests.get')
    def test_get_csv(self, m_get, m_reader):
        m_response = mock.MagicMock(ok=True, content=b"")
        m_get.return_value = m_response
        output = ruck_rover.get_csv("")
        self.assertEqual(output, ['', m_reader()])

    def test_get_dlrn_results(self):
        periodic_passed = mock.MagicMock(
            job_id="periodic_job",
            success=True,
            timestamp=1,
            url="https://periodic_passed_url"
        )
        periodic_failed = mock.MagicMock(
            job_id="periodic_job",
            success=False,
            timestamp=2,
            url="https://periodic_failed_url"
        )
        periodic_failed_newer = mock.MagicMock(
            job_id="periodic_job",
            success=False,
            timestamp=7,
            url="https://periodic_failed_newer_url"
        )
        pipeline_passed = mock.MagicMock(
            job_id="pipeline_job",
            success=True,
            timestamp=3,
            url="https://pipeline_passed_url"
        )
        pipeline_failed = mock.MagicMock(
            job_id="pipeline_job",
            success=False,
            timestamp=4,
            url="https://pipeline_failed_url"
        )
        pipeline_passed_newer = mock.MagicMock(
            job_id="pipeline_job",
            success=True,
            timestamp=8,
            url="https://pipeline_passed_newer_url"
        )
        ignored_passed = mock.MagicMock(
            job_id="ignored_job",
            success=True,
            timestamp=5,
            url="https://ignored_passed_url"
        )
        ignored_failed = mock.MagicMock(
            job_id="ignored_job",
            success=False,
            timestamp=6,
            url="https://ignored_failed_url"
        )
        api_response = [
            periodic_passed,
            periodic_failed,
            pipeline_passed,
            pipeline_failed,
            ignored_passed,
            ignored_failed,
            periodic_failed_newer,
            pipeline_passed_newer,
        ]
        results = ruck_rover.get_dlrn_results(api_response)
        expected = {
            'periodic_job': periodic_passed,
            'pipeline_job': pipeline_passed_newer,
        }
        self.assertEqual(expected, results)

    def test_get_dlrn_results_fail(self):
        periodic_failed1 = mock.MagicMock(
            job_id="periodic_job",
            success=False,
            timestamp=1,
            url="https://periodic_passed_url"
        )
        periodic_failed2 = mock.MagicMock(
            job_id="periodic_job",
            success=False,
            timestamp=2,
            url="https://periodic_failed_url"
        )
        periodic_failed3 = mock.MagicMock(
            job_id="periodic_job",
            success=False,
            timestamp=3,
            url="https://periodic_failed_newer_url"
        )
        api_response = [
                periodic_failed1,
                periodic_failed2,
                periodic_failed3,
        ]
        results = ruck_rover.get_dlrn_results(api_response)
        expected = {
            'periodic_job': periodic_failed3,
        }
        self.assertEqual(expected, results)


class TestRuckRoverComponent(unittest.TestCase):
    def setUp(self):
        self.config = {
            'downstream': {
                'testproject_url':
                'https://review.rdoproject.org/r/q/project:testproject',
                'periodic_builds_url':
                'https://review.rdoproject.org/zuul/api/builds',
                'upstream_builds_url': 'https://zuul.openstack.org/api/builds',
                'criteria': {
                    'centos-8': {
                        'wallaby': {
                            'comp_url': 'http://wallaby_comp',
                            'int_url': 'http://int_url'
                                   }
                               },
                }
            }
        }

    def test_get_components_diff_all(self):
        result = ruck_rover.get_components_diff("base_url", "all", "", "")
        all_components = ["baremetal", "cinder", "clients", "cloudops",
                          "common", "compute", "glance", "manila",
                          "network", "octavia", "security", "swift",
                          "tempest", "tripleo", "ui", "validation"]
        expected = (all_components, None)
        self.assertEqual(result, expected)

    @mock.patch('ruck_rover.get_diff')
    @mock.patch('ruck_rover.get_csv')
    def test_get_components_single(self, m_csv, m_diff):

        m_csv.side_effect = ["first", "second"]
        m_diff.return_value = "pkg_diff"

        result = ruck_rover.get_components_diff(
            "base_url", "cinder", "current-tripleo",
            "component-ci-testing")

        m_csv.assert_has_calls([
            call('base_url/component/cinder/current-tripleo/versions.csv'),
            call('base_url/component/cinder/component-ci-testing/versions.csv')
        ])

        m_diff.assert_called_with(
            "current-tripleo", "first", "component-ci-testing", "second")

        expected = (['cinder'], "pkg_diff")
        self.assertEqual(result, expected)

    @mock.patch('ruck_rover.dlrnapi_client.PromotionQuery')
    @mock.patch('ruck_rover.dlrnapi_client.DefaultApi')
    @mock.patch('ruck_rover.dlrnapi_client.ApiClient')
    def test_get_dlrn_promotions(
            self, m_api_client, m_def_api, m_promo_query):
        m_api = mock.MagicMock()
        m_pr = mock.MagicMock()
        m_api.api_promotions_get.return_value = [m_pr]
        m_def_api.return_value = m_api

        result = ruck_rover.get_dlrn_promotions("api_url", "promotion", None)

        m_api_client.assert_called_with(host="api_url",
                                        auth_method='kerberosAuth',
                                        force_auth=True)
        m_promo_query.assert_called_with(
            promote_name="promotion", limit=1, component=None)

        self.assertEqual(result, m_pr)


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
        mock_resp = self._mock_response(json_data=json.loads(self.data))
        mock_get.return_value = mock_resp
        job = ("periodic-tripleo-ci-centos-8-standalone-full-tempest-"
               "scenario-master")
        zb_periodic = "https://review.rdoproject.org/zuul/api/builds"
        history = ruck_rover.get_job_history([job], zb_periodic)
        self.assertIn(job, history.keys())
        self.assertEqual(history[job]['SUCCESS'], 3)
        self.assertEqual(history[job]['FAILURE'], 2)
        self.assertEqual(history[job]['OTHER'], 0)


if __name__ == '__main__':
    unittest.main()
