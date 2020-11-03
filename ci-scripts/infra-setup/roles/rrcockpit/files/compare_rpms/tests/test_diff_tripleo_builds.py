import json
import os
import unittest

import mock
from diff_tripleo_builds import diff_builds

# execute w/ python -m unittest

# sys.path.append(os.path.abspath('..'))


class TestDiffTripleOBuilds(unittest.TestCase):

    def setUp(self):
        self.diff = diff_builds.DiffBuilds()
        # from get_logs, nice_list
        self.control_list = {'fribidi-1.0.4-8.el8',
                             'fribidi-1.0.5-9.el8',
                             'fribidi-1.0.5-11.el8',
                             'python3-pyasn1-modules-0.4.6-3.el8.noarch',
                             'lvm2-8:2.03.08-3.el8',
                             'python3-pip-wheel-9.0.3-16.el8',
                             'foo-8:2.8.08-3.el8'
                             }
        self.test_list = {'fribidi-1.0.5-8.el8',
                          'python3-pyasn1-modules-0.4.6-3.el8.noarch',
                          'lvm2-8:2.04.08-3.el8',
                          'python3-pip-wheel-9.0.3-16.el8',
                          'bar-8:2.8.08-3.el8'
                          }

        self.version_list = {'foobar-1.0.0-2.el8',
                             'foobar-1.0.1-2.el8',
                             'foobar-1.1.0-2.el8',
                             'foobar-1.1.0-99.el8'
                             }
        self.ignore_packages_empty = {}
        self.rpms_control_json = {}
        self.rpms_test_json = {}

        full_path = os.path.dirname(os.path.abspath(__file__))
        with open(full_path + '/rpms_control.json') as json_file:
            self.rpms_control_json = json.load(json_file)

        with open(full_path + '/rpms_test.json') as json_file:
            self.rpms_test_json = json.load(json_file)

        with open(full_path + '/container_rpms.txt') as file:
            self.container_rpms = file.read()

        with open(full_path + '/upstream_container_list.txt') as file:
            self.upstream_container_html = file.read()

        with open(full_path + '/downstream_container_list.txt') as file:
            self.downstream_container_html = file.read()

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
    def test_upstream_containers_dir(self, mock_get):
        # the containers directory is rendered in
        # different ways upstream/downstream
        html = self.upstream_container_html
        mock_resp = self._mock_response(content=html)
        mock_get.return_value = mock_resp
        containers = self.diff.get_directory_list("foo", "undercloud")
        self.assertEqual(len(containers), 72)
        self.assertEqual(containers[0], 'container-puppet-crond')
        self.assertEqual(containers[71], 'tempest_init_logs')

    @mock.patch('requests.get')
    def test_downstream_containers_dir(self, mock_get):
        # the containers directory is rendered in
        # different ways upstream/downstream
        html = self.downstream_container_html
        mock_resp = self._mock_response(content=html)
        mock_get.return_value = mock_resp
        containers = self.diff.get_directory_list("foo", "undercloud")
        self.assertEqual(len(containers), 38)
        self.assertEqual(containers[0], 'create_swift_temp_url_key')
        self.assertEqual(containers[37], 'zaqar_websocket')

    def test_parse_container_rpms(self):
        # start after the log file has been split
        # into container info and rpm_info
        dict_of_containers = {}
        container_info_temp = self.container_rpms.split("\n")
        dict_of_containers["test_container"] = container_info_temp
        parsed_list = self.diff.process_containers_step2(dict_of_containers)
        self.assertEqual(len(parsed_list['test_container']), 40)

    def test_parse_list_control(self):
        result = self.diff.parse_list(self.control_list)
        self.assertEqual(len(self.control_list), 7)
        self.assertEqual(len(result), 5)
        self.assertIn(('1.0.4', '8.el8'), result['fribidi'])
        self.assertIn(('1.0.5', '11.el8'), result['fribidi'])
        self.assertIn(('1.0.5', '9.el8'), result['fribidi'])

    def test_parse_list_test(self):
        result = self.diff.parse_list(self.test_list)
        self.assertEqual(len(self.test_list), 5)
        self.assertEqual(len(result), 5)

    def test_find_highest_version(self):
        packages = self.diff.parse_list(
            self.control_list, )
        result = self.diff.find_highest_version(packages)
        self.assertEqual(len(result), 5)
        self.assertNotIn('1.0.4', result['fribidi'])
        self.assertEqual(['1.0.5', '1.0.5-11.el8'], result['fribidi'])

    def test_nvr(self):
        packages = self.diff.parse_list(
            self.version_list, )
        result = self.diff.find_highest_version(packages)
        self.assertEqual(len(packages), 1)
        self.assertEqual(['1.1.0', '1.1.0-99.el8'], result['foobar'])

    def test_diff_packages(self):
        c_packages = self.diff.parse_list(
            self.control_list, self.ignore_packages_empty)
        t_packages = self.diff.parse_list(
            self.test_list, self.ignore_packages_empty)
        c_highest = self.diff.find_highest_version(c_packages)
        t_highest = self.diff.find_highest_version(t_packages)
        package_diff = self.diff.diff_packages(
            c_highest, t_highest)
        # ensure package diff has the right packages
        self.assertEqual(len(package_diff), 4)
        self.assertIn('foo', package_diff.keys())
        self.assertIn('bar', package_diff.keys())
        self.assertIn('lvm2', package_diff.keys())
        # ensure package in control but not test is correct
        self.assertEqual(['2.8.08', '2.8.08-3.el8'], package_diff['foo'][0])
        self.assertEqual(['0', 'not installed'], package_diff['foo'][1])
        # ensure package in test but not control is correct
        self.assertEqual(['0', 'not installed'], package_diff['bar'][0])
        self.assertEqual(['2.8.08', '2.8.08-3.el8'], package_diff['bar'][1])

    def test_ignore_packages(self):
        ignore_packages = {"fribidi", "python3-pyasn1-modules",
                           "lvm2", "python3-pip-wheel"
                           }
        c_packages = self.diff.parse_list(
            self.control_list, ignore_packages=ignore_packages)
        t_packages = self.diff.parse_list(
            self.test_list, ignore_packages=ignore_packages)
        c_highest = self.diff.find_highest_version(c_packages)
        t_highest = self.diff.find_highest_version(t_packages)
        package_diff = self.diff.diff_packages(
            c_highest, t_highest)

        package_foo = [['2.8.08', '2.8.08-3.el8'], ['0', 'not installed']]
        package_bar = [['0', 'not installed'], ['2.8.08', '2.8.08-3.el8']]
        self.assertEqual(len(package_diff), 2)
        self.assertEqual(package_foo, package_diff['foo'])
        self.assertEqual(package_bar, package_diff['bar'])

    def test_compose_dir(self):
        control_list = self.rpms_control_json
        test_list = self.rpms_test_json
        c_packages = self.diff.parse_compose(control_list)
        t_packages = self.diff.parse_compose(test_list)
        c_packages = self.diff.parse_list(c_packages)
        t_packages = self.diff.parse_list(t_packages)
        c_highest = self.diff.find_highest_version(c_packages)
        t_highest = self.diff.find_highest_version(t_packages)
        package_diff = self.diff.diff_packages(c_highest, t_highest)
        self.assertEqual(len(package_diff), 1045)


if __name__ == '__main__':
    unittest.main()
