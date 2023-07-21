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

    def test_short_find_failure_reason(self):
        obtained = ruck_rover.find_failure_reason('N/A')
        self.assertEqual("N/A", obtained)

    @patch('ruck_rover.requests.get')
    def test_find_failure_reason(self, m_get):
        full_path = os.path.dirname(os.path.abspath(__file__))
        # to-do correct path when move test file to correct place
        with open(full_path + "/data/failures_file") as file:
            data = file.read()
        m_get.return_value.text = data
        m_get.return_value.ok = True
        expected = "Tempest tests failed. Reason: code "
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
        criteria = {
            'api_url': 'https://trunk.rdoproject.org/api-centos8-master-uc',
            'base_url': 'https://trunk.rdoproject.org/centos8-master/'
        }

        a_url = 'https://trunk.rdoproject.org/api-centos8-master-uc'
        b_url = 'https://trunk.rdoproject.org/centos8-master/'
        expected = (a_url, b_url)
        obtained = ruck_rover.gather_basic_info_from_criteria(criteria)
        self.assertEqual(obtained, expected)

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
    def test_get_last_modified_date_centos9_no_component(self, m_get):
        m_get.return_value.ok = None
        cert_path = '/etc/pki/ca-trust/extracted/openssl/ca-bundle.trust.crt'

        url = 'https://trunk.rdoproject.org/centos9-master/'
        ruck_rover.get_last_modified_date(url, component=None)
        expected = ('https://trunk.rdoproject.org/centos9-master/'
                    'promoted-components/delorean.repo')
        m_get.assert_called_with(expected,
                                 verify=cert_path)

    @patch('ruck_rover.requests.get')
    def test_get_last_modified_date_centos8_with_component(self, m_get):
        m_get.return_value.ok = None
        cert_path = '/etc/pki/ca-trust/extracted/openssl/ca-bundle.trust.crt'

        url = 'https://trunk.rdoproject.org/centos8-wallaby/'
        ruck_rover.get_last_modified_date(url, component="cinder")
        expected = ('https://trunk.rdoproject.org/centos8-wallaby/component/'
                    'cinder/consistent/delorean.repo')
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
            'upstream': {
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

    @mock.patch('ruck_rover.prepare_jobs')
    @mock.patch('ruck_rover.find_jobs_in_component_criteria')
    @mock.patch('ruck_rover.find_results_from_dlrn_repo_status')
    @mock.patch('ruck_rover.fetch_hashes_from_commit_yaml')
    @mock.patch('ruck_rover.get_last_modified_date')
    @mock.patch('ruck_rover.get_dlrn_promotions')
    @mock.patch('ruck_rover.get_diff')
    @mock.patch('ruck_rover.get_csv')
    @mock.patch('ruck_rover.get_dlrn_versions_csv')
    @mock.patch('ruck_rover.gather_basic_info_from_criteria')
    @mock.patch('ruck_rover.url_response_in_yaml')
    def test_all_components(
            self, m_yaml, m_gather, m_dlrn, m_csv, m_diff, m_promo,
            m_consistent, m_fetch, _m_results, _m_jobs, _m_prepare):
        m_gather.return_value = ('api_url', 'base_url')
        m_fetch.return_value = ('c6', '03', 'None')
        m_dlrn.side_effect = ['control_url', 'test_url']
        m_csv.side_effect = ["first", "second"]

        ruck_rover.component_influx(
            self.config, 'centos-8', 'wallaby', 'upstream', 'all')

        m_yaml.assert_any_call("http://wallaby_comp")
        m_dlrn.assert_not_called()
        m_csv.assert_not_called()
        m_diff.assert_not_called()

    @mock.patch('ruck_rover.prepare_jobs')
    @mock.patch('ruck_rover.find_jobs_in_component_criteria')
    @mock.patch('ruck_rover.get_dlrn_results')
    @mock.patch('ruck_rover.find_results_from_dlrn_repo_status')
    @mock.patch('ruck_rover.get_last_modified_date')
    @mock.patch('ruck_rover.get_dlrn_promotions')
    @mock.patch('ruck_rover.fetch_hashes_from_commit_yaml')
    @mock.patch('ruck_rover.get_components_diff')
    @mock.patch('ruck_rover.gather_basic_info_from_criteria')
    @mock.patch('ruck_rover.url_response_in_yaml')
    def test_given_component(
            self, m_yaml, m_gather, m_comp_diff, m_fetch, m_promo,
            m_consistent, m_results, _m_dlrn_results, _m_jobs, _m_prepare):

        component = "cinder"
        commit_hash = "c6"
        distro_hash = "03"
        extended_hash = 'None'

        m_gather.return_value = ('api_url', 'base_url/')
        m_comp_diff.return_value = ([component], None)
        m_fetch.return_value = (commit_hash, distro_hash, extended_hash)
        m_results.return_value = "api_response"
        promotion = mock.MagicMock(
            commit_hash=commit_hash,
            distro_hash=distro_hash,
            timestamp=1,
            latest_build=1,
            repo_url='repo_url',
        )
        m_promo.return_value = promotion

        ruck_rover.component_influx(
            self.config, 'centos-8', 'wallaby', 'upstream', component)

        m_yaml.assert_any_call("http://wallaby_comp")
        m_results.assert_called_with(
            "api_url", commit_hash, distro_hash, extended_hash)
        m_promo.assert_called_with("api_url", "promoted-components", "cinder")

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
    @mock.patch('ruck_rover.get_dlrn_versions_csv')
    def test_get_components_single(self, m_dlrn, m_csv, m_diff):

        m_dlrn.side_effect = ['control_url', 'test_url']
        m_csv.side_effect = ["first", "second"]
        m_diff.return_value = "pkg_diff"

        result = ruck_rover.get_components_diff(
            "base_url", "cinder", "current-tripleo",
            "component-ci-testing")

        m_dlrn.assert_has_calls([
            call('base_url', 'cinder', 'current-tripleo'),
            call('base_url', 'cinder', 'component-ci-testing')
        ])
        m_csv.assert_has_calls([call('control_url'), call('test_url')])
        m_diff.assert_called_with(
            "current-tripleo", "first", "component-ci-testing", "second")

        expected = (['cinder'], "pkg_diff")
        self.assertEqual(result, expected)

    @mock.patch('ruck_rover.get_last_modified_date')
    @mock.patch('ruck_rover.dlrnapi_client.PromotionQuery')
    @mock.patch('ruck_rover.dlrnapi_client.DefaultApi')
    @mock.patch('ruck_rover.dlrnapi_client.ApiClient')
    def test_get_dlrn_promotions(
            self, m_api_client, m_def_api, m_promo_query, m_consistent):
        m_consistent.return_value = "consistent"
        m_api = mock.MagicMock()
        m_pr = mock.MagicMock()
        m_api.api_promotions_get.return_value = [m_pr]
        m_def_api.return_value = m_api

        result = ruck_rover.get_dlrn_promotions("api_url", "promotion", None)

        m_api_client.assert_called_with(host="api_url",
                                        auth_method='basicAuth',
                                        force_auth=False)
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


@mock.patch('builtins.print')
@mock.patch('ruck_rover.query_zuul_job_details')
@mock.patch('ruck_rover.latest_job_results_url')
@mock.patch('ruck_rover.find_jobs_in_integration_alt_criteria')
@mock.patch('ruck_rover.find_jobs_in_integration_criteria')
@mock.patch('ruck_rover.find_results_from_dlrn_agg')
@mock.patch('ruck_rover.web_scrape')
@mock.patch('ruck_rover.find_failure_reason')
@mock.patch('ruck_rover.find_jobs_in_component_criteria')
@mock.patch('ruck_rover.get_dlrn_results')
@mock.patch('ruck_rover.find_results_from_dlrn_repo_status')
@mock.patch('ruck_rover.fetch_hashes_from_commit_yaml')
@mock.patch('ruck_rover.get_last_modified_date')
@mock.patch('ruck_rover.get_dlrn_promotions')
@mock.patch('ruck_rover.get_components_diff')
@mock.patch('ruck_rover.gather_basic_info_from_criteria')
class TestInfluxDBMeasurements(unittest.TestCase):
    def setUp(self):
        self.config = {
            'upstream': {
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
        self.distro = "centos-8"
        self.release = "wallaby"
        self.influx = True
        self.stream = "upstream"

    def test_component(
            self, m_gather, m_get_comp, m_get_promo, m_consistent, m_fetch_hash,
            m_find_results, m_dlrn, m_find_jobs_comp, m_reason, m_web_scrape,
            m_find_result_aggr, _m_find_jobs_int, _m_find_jobs_alt_criteria,
            m_latest_job, m_zuul, m_print):
        component = "all"

        component = "cinder"
        commit_hash = "c6"
        distro_hash = "03"
        extended_hash = 'None'

        m_gather.return_value = ('api_url', 'base_url')
        m_get_comp.return_value = ([component], None)
        promotion = mock.MagicMock(
            commit_hash=commit_hash,
            distro_hash=distro_hash,
            timestamp=1,
            latest_build=1,
            repo_hash='repo_hash',
            repo_url='repo_url',
            aggregate_hash='hash',
            promote_name='promo',
            component=component,
            extended_hash=extended_hash,
        )

        m_get_promo.return_value = promotion
        m_fetch_hash.return_value = (commit_hash, distro_hash, extended_hash)
        m_dlrn.return_value = {
            'passed': mock.MagicMock(
                job_id="passed",
                success=True,
                timestamp=1,
                url="logs",
            ),
            'failed': mock.MagicMock(
                job_id="failed",
                success=False,
                timestamp=7,
                url="logs",
            ),
            'pending': mock.MagicMock(
                job_id='pending',
                timestamp=8,
                url="logs",
            )
        }
        m_reason.return_value = "N/A"
        m_web_scrape.return_value = "test_hash"
        m_find_jobs_comp.return_value = set(["passed", "failed", "pending"])
        m_zuul.return_value = {}
        m_latest_job.return_value = {}

        ruck_rover.component_influx(
            self.config, self.distro, self.release, self.stream, component)

        job1 = ('jobs_result,job_type=component,job_name=failed'
                ',release=wallaby name="promoted-components",test_hash="c6_03"'
                ',criteria="True",status="0",logs="logs/",failure_reason="N/A"'
                ',duration="00 hr 00 mins 00 secs",component="cinder"'
                ',distro="centos-8"')
        job2 = ('jobs_result,job_type=component,job_name=passed'
                ',release=wallaby name="promoted-components",test_hash="c6_03"'
                ',criteria="True",status="9",logs="logs/",failure_reason="N/A"'
                ',duration="00 hr 00 mins 00 secs",component="cinder"'
                ',distro="centos-8"')
        job3 = ('jobs_result,job_type=component,job_name=pending'
                ',release=wallaby name="promoted-components",test_hash="c6_03"'
                ',criteria="True",status="5",logs="logs/",failure_reason="N/A"'
                ',duration="00 hr 00 mins 00 secs",component="cinder"'
                ',distro="centos-8"')
        dlrn = ('dlrn-promotion,release=wallaby,distro=centos-8'
                ',promo_name=promo commit_hash="c6",distro_hash="03"'
                ',aggregate_hash="hash",repo_hash="repo_hash"'
                ',repo_url="repo_url",latest_build_date=1000'
                ',component="cinder",promotion_details="api_url/api/'
                'civotes_detail.html?commit_hash=c6&distro_hash=03"'
                ',extended_hash="None" 1000000000')

        output = '\n'.join([job1, job2, job3, dlrn])
        m_print.assert_called_once_with(output)

    def test_integration(
            self, m_gather, m_get_comp, m_get_promo, m_consistent, m_fetch_hash,
            m_find_results, m_dlrn, _m_find_jobs_comp, m_reason,
            m_web_scrape, _m_find_result_aggr, m_find_jobs_int,
            m_find_jobs_alt_criteria, m_latest_job, m_zuul, m_print):
        promotion_name = "promote_name"

        commit_hash = "c6"
        distro_hash = "03"
        extended_hash = 'None'

        m_gather.return_value = ('api_url', 'base_url')
        m_get_comp.return_value = ([None], None)
        promotion = mock.MagicMock(
            commit_hash=commit_hash,
            distro_hash=distro_hash,
            timestamp=1,
            latest_build=1,
            aggregate_hash='hash',
            promote_name='promo',
            repo_hash='repo_hash',
            repo_url='repo_url',
            component=None,
            extended_hash=extended_hash,
        )

        m_get_promo.return_value = promotion
        m_fetch_hash.return_value = (commit_hash, distro_hash, extended_hash)
        m_find_results.return_value = "api_response"
        m_dlrn.return_value = {
            'passed': mock.MagicMock(
                job_id="passed",
                success=True,
                timestamp=1,
                url="logs",
            ),
            'failed': mock.MagicMock(
                job_id="failed",
                success=False,
                timestamp=7,
                url="logs",
            ),
            'pending': mock.MagicMock(
                job_id='pending',
                timestamp=8,
                url="logs",
            )
        }
        m_reason.return_value = "N/A"
        m_web_scrape.return_value = "test_hash"
        m_find_jobs_int.return_value = set(["passed", "failed", "pending"])
        m_find_jobs_alt_criteria.return_value = dict()
        m_zuul.return_value = {}
        m_latest_job.return_value = {}

        ruck_rover.integration_influx(
            self.config, self.distro, self.release, self.stream, promotion_name)

        job1 = ('jobs_result,job_type=integration,job_name=failed'
                ',release=wallaby name="promote_name",test_hash="test_hash"'
                ',criteria="True",status="0",logs="logs/",failure_reason="N/A"'
                ',duration="00 hr 00 mins 00 secs",component="None"'
                ',distro="centos-8"')
        job2 = ('jobs_result,job_type=integration,job_name=passed'
                ',release=wallaby name="promote_name",test_hash="test_hash"'
                ',criteria="True",status="9",logs="logs/",failure_reason="N/A"'
                ',duration="00 hr 00 mins 00 secs",component="None"'
                ',distro="centos-8"')
        job3 = ('jobs_result,job_type=integration,job_name=pending'
                ',release=wallaby name="promote_name",test_hash="test_hash"'
                ',criteria="True",status="5",logs="logs/",failure_reason="N/A"'
                ',duration="00 hr 00 mins 00 secs",component="None"'
                ',distro="centos-8"')
        dlrn = ('dlrn-promotion,release=wallaby,distro=centos-8'
                ',promo_name=promo commit_hash="c6",distro_hash="03"'
                ',aggregate_hash="hash",repo_hash="repo_hash"'
                ',repo_url="repo_url",latest_build_date=1000,component="None"'
                ',promotion_details="api_url/api/civotes_agg_detail.html'
                '?ref_hash=hash",extended_hash="None" 1000000000')

        output = '\n'.join([job1, job2, job3, dlrn])
        m_print.assert_called_once_with(output)


class TestRuckRoverInflux(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    @mock.patch('ruck_rover.find_failure_reason')
    @mock.patch('ruck_rover.query_zuul_job_details')
    def test_empty_prepare_jobs(self, m_zuul, m_failure_reason):
        jobs = {}
        jobs_in_criteria = set()

        result = ruck_rover.prepare_jobs(jobs_in_criteria, {}, jobs, False)
        self.assertEqual([], result)

    @mock.patch('ruck_rover.find_failure_reason')
    @mock.patch('ruck_rover.query_zuul_job_details')
    def test_prepare_jobs(self, m_zuul, m_failure_reason):
        m_failure_reason.return_value = 'failure_reason'
        m_zuul.return_value = {'duration': 0}

        job_a = mock.MagicMock(
            job_id="job_a",
            success=True,
            url="https://job_a_url"
        )
        job_c = mock.MagicMock(
            job_id="job_c",
            success=True,
            url="https://job_c_url"
        )
        job_d = mock.MagicMock(
            job_id="job_d",
            success=False,
            url="https://job_d_url"
        )
        jobs = {
            'job_a': job_a,
            'job_c': job_c,
            'job_d': job_d
        }
        jobs_in_criteria = set(['job_b', 'job_c', 'job_d'])

        result = ruck_rover.prepare_jobs(jobs_in_criteria, {}, jobs, False)
        expected = [
            {
                'job_name': 'job_a',
                'criteria': False,
                'alt_criteria': [],
                'logs': 'https://job_a_url/',
                'duration': '00 hr 00 mins 00 secs',
                'status': ruck_rover.INFLUX_PASSED,
                'failure_reason': 'N/A',
            },
            {
                'job_name': 'job_b',
                'criteria': True,
                'alt_criteria': [],
                'logs': 'N/A',
                'duration': '00 hr 00 mins 00 secs',
                'status': ruck_rover.INFLUX_PENDING,
                'failure_reason': 'N/A',
            },
            {
                'job_name': 'job_c',
                'criteria': True,
                'alt_criteria': [],
                'logs': 'https://job_c_url/',
                'duration': '00 hr 00 mins 00 secs',
                'status': ruck_rover.INFLUX_PASSED,
                'failure_reason': 'N/A',
            },
            {
                'job_name': 'job_d',
                'criteria': True,
                'alt_criteria': [],
                'logs': 'https://job_d_url/',
                'duration': '00 hr 00 mins 00 secs',
                'status': ruck_rover.INFLUX_FAILED,
                'failure_reason': 'failure_reason',
            }
        ]
        self.assertEqual(expected, result)


if __name__ == '__main__':
    unittest.main()
