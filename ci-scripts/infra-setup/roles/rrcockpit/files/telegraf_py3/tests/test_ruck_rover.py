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


if __name__ == '__main__':
    unittest.main()
