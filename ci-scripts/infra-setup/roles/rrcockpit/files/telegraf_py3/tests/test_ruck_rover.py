import os
import unittest
from datetime import datetime
from unittest import mock
from unittest.mock import call, patch

import ruck_rover


class TestRuckRover(unittest.TestCase):
    # pylint: disable=too-many-public-methods

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
            expected = set([
                'periodic-tripleo-baremetal-master',
                'periodic-tripleo-sc012-baremetal-master'])
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
        obtained = ruck_rover.load_conf_file(my_file)
        expected = {'upstream': {'zuul_url': 'abc',
                                 'dlrnapi_url': 'def',
                                 'promoter_url': 'ghi',
                                 'git_url': 'jkl'}}
        self.assertEqual(expected, obtained)

    @patch('ruck_rover.requests.get')
    def test_get_consistent_centos9_no_component(self, m_get):
        m_get.return_value.ok = None
        cert_path = '/etc/pki/ca-trust/extracted/openssl/ca-bundle.trust.crt'

        url = ('https://trunk.rdoproject.org/centos9-master/component/network/'
               '39/40/3940e9eb4a6e0652517c4f2c429e601332ad1bd9_48ca9c7b')
        ruck_rover.get_consistent(url, component=None)
        expected = ('https://trunk.rdoproject.org/centos9-master/'
                    'promoted-components/delorean.repo')
        m_get.assert_called_with(expected,
                                 verify=cert_path)

    @patch('ruck_rover.requests.get')
    def test_get_consistent_centos8_with_component(self, m_get):
        m_get.return_value.ok = None
        cert_path = '/etc/pki/ca-trust/extracted/openssl/ca-bundle.trust.crt'

        url = ('https://trunk.rdoproject.org/centos8-wallaby/component/cinder/'
               '0a/6d/0a6d43a7c2ef65be748690a00ee4c294add0c87c_cc0b2aef')
        ruck_rover.get_consistent(url, component="cinder")
        expected = ('https://trunk.rdoproject.org/centos8-wallaby/component/'
                    'cinder/consistent/delorean.repo')
        m_get.assert_called_with(expected,
                                 verify=cert_path)

    @patch('ruck_rover.requests.get')
    def test_get_consistent_centos7_no_component(self, m_get):
        m_get.return_value.ok = None
        cert_path = '/etc/pki/ca-trust/extracted/openssl/ca-bundle.trust.crt'

        url = ('https://trunk.rdoproject.org/centos7-train/08/bb/'
               '08bbadedb04d45353b3228bc21cd930adeef3348_0ad01be2')
        ruck_rover.get_consistent(url, component=None)
        expected = ("https://trunk.rdoproject.org/centos7-train/"
                    "consistent/delorean.repo")
        m_get.assert_called_with(expected,
                                 verify=cert_path)

    def test_get_dlrn_versions_csv_no_component(self):
        base_url = "base_url"
        component = None
        tag = "tag"

        output = ruck_rover.get_dlrn_versions_csv(base_url, component, tag)
        expected = f"{base_url}/{tag}/versions.csv"
        self.assertEqual(expected, output)

    def test_get_dlrn_versions_csv_component(self):
        base_url = "base_url"
        component = "component"
        tag = "tag"

        output = ruck_rover.get_dlrn_versions_csv(base_url, component, tag)
        expected = f"{base_url}/component/{component}/{tag}/versions.csv"
        self.assertEqual(expected, output)

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


class TestRuckRoverComponent(unittest.TestCase):
    def setUp(self):
        self.config = {
            'upstream': {
                'criteria': {
                    'centos-8': {
                        'wallaby': {
                            'comp_url': 'http://wallaby_comp',
                            'int_url': 'http://int_url'
                                   }
                               },
                    'centos-7': {
                        'train': {
                            'int_url': 'http://int_url'
                                   }
                               }
                           }
                       }
                   }

    def test_track_component_promotion_centos7(self):
        distro = 'centos-7'
        release = 'train'
        influx = False
        stream = 'upstream'
        compare_upstream = False
        component = 'cinder'

        with self.assertRaises(Exception):
            ruck_rover.track_component_promotion(
                self.config, distro, release, influx, stream,
                compare_upstream, component)

    @mock.patch('ruck_rover.find_jobs_in_component_criteria')
    @mock.patch('ruck_rover.conclude_results_from_dlrn')
    @mock.patch('ruck_rover.find_results_from_dlrn_repo_status')
    @mock.patch('ruck_rover.fetch_hashes_from_commit_yaml')
    @mock.patch('ruck_rover.get_dlrn_promotions')
    @mock.patch('ruck_rover.get_diff')
    @mock.patch('ruck_rover.get_csv')
    @mock.patch('ruck_rover.get_dlrn_versions_csv')
    @mock.patch('ruck_rover.gather_basic_info_from_criteria')
    def test_all_components(
            self, m_gather, m_dlrn, m_csv, m_diff,
            m_promo, m_fetch, _m_results, m_conclude, _m_jobs):
        m_gather.return_value = ('dlrn_api_url', 'dlrn_trunk_url')
        m_fetch.return_value = ('c6', '03', 'None')
        m_dlrn.side_effect = ['control_url', 'test_url']
        m_csv.side_effect = ["first", "second"]
        m_conclude.return_value = set(), set(), set()

        ruck_rover.track_component_promotion(
            self.config, 'centos-8', 'wallaby', 'influx',
            'upstream', compare_upstream=False, test_component='all')

        m_gather.assert_called_with("http://wallaby_comp")
        m_dlrn.assert_not_called()
        m_csv.assert_not_called()
        m_diff.assert_not_called()

    @mock.patch('ruck_rover.find_jobs_in_component_criteria')
    @mock.patch('ruck_rover.conclude_results_from_dlrn')
    @mock.patch('ruck_rover.find_results_from_dlrn_repo_status')
    @mock.patch('ruck_rover.get_dlrn_promotions')
    @mock.patch('ruck_rover.fetch_hashes_from_commit_yaml')
    @mock.patch('ruck_rover.get_components_diff')
    @mock.patch('ruck_rover.gather_basic_info_from_criteria')
    def test_given_component(
            self, m_gather, m_comp_diff, m_fetch, m_promo,
            m_results, m_conclude, _m_jobs):

        component = "cinder"
        commit_hash = "c6"
        distro_hash = "03"
        extended_hash = 'None'

        m_gather.return_value = ('dlrn_api_url', 'dlrn_trunk_url/')
        m_comp_diff.return_value = ([component], None)
        m_fetch.return_value = (commit_hash, distro_hash, extended_hash)
        m_results.return_value = "api_response"
        m_promo.return_value = {
            'commit_hash': commit_hash,
            'distro_hash': distro_hash
        }
        m_conclude.return_value = set(), set(), set()

        ruck_rover.track_component_promotion(
            self.config, 'centos-8', 'wallaby', 'influx',
            'upstream', compare_upstream=False, test_component=component)

        m_gather.assert_called_with("http://wallaby_comp")
        m_fetch.assert_called_with(
            "dlrn_trunk_url/component/cinder/component-ci-testing/commit.yaml")
        m_results.assert_called_with(
            "dlrn_api_url", commit_hash, distro_hash, extended_hash)
        m_promo.assert_called_with(
            "dlrn_api_url", "promoted-components", component="cinder")

    def test_get_components_diff_all(self):
        result = ruck_rover.get_components_diff("dlrn_trunk_url", "all", "", "")
        all_components = ["baremetal", "cinder", "clients", "cloudops",
                          "common", "compute", "glance", "manila",
                          "network", "octavia", "security", "swift",
                          "tempest", "tripleo", "ui", "validation"]
        expected = (all_components, None)
        self.assertEqual(result, expected)

    @mock.patch('ruck_rover.get_diff')
    @mock.patch('ruck_rover.get_csv')
    @mock.patch('ruck_rover.get_dlrn_versions_csv')
    def test_get_components_single(self, m_dlrn, m_csv, m_diff):

        m_dlrn.side_effect = ['control_url', 'test_url']
        m_csv.side_effect = ["first", "second"]
        m_diff.return_value = "pkg_diff"

        result = ruck_rover.get_components_diff(
            "dlrn_trunk_url", "cinder", "1", "2")

        m_dlrn.assert_has_calls([
            call('dlrn_trunk_url', 'cinder', '1'),
            call('dlrn_trunk_url', 'cinder', '2')
        ])
        m_csv.assert_has_calls([call('control_url'), call('test_url')])
        m_diff.assert_called_with(
            "1", "first", "2", "second")

        expected = (['cinder'], "pkg_diff")
        self.assertEqual(result, expected)

    @mock.patch('ruck_rover.get_consistent')
    @mock.patch('ruck_rover.dlrnapi_client.PromotionQuery')
    @mock.patch('ruck_rover.dlrnapi_client.DefaultApi')
    @mock.patch('ruck_rover.dlrnapi_client.ApiClient')
    def test_get_dlrn_promotions(
            self, m_api_client, m_def_api, m_promo_query, m_consistent):
        m_consistent.return_value = "consistent"
        m_api = mock.MagicMock()
        m_pr = mock.MagicMock()
        m_pr.to_dict.return_value = {'abc': 'def'}
        m_api.api_promotions_get_with_http_info.return_value = [[m_pr]]
        m_def_api.return_value = m_api

        result = ruck_rover.get_dlrn_promotions("api_url", "promotion", None)

        m_api_client.assert_called_with(host="api_url")
        m_promo_query.assert_called_with(limit=1, promote_name="promotion")

        expected = {'abc': 'def', 'lastest_build': 'consistent'}

        self.assertEqual(result, expected)


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
