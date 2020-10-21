import json
import os
import unittest
import sys
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
        test_full_path = os.path.abspath('rpms_test.json')
        with open(full_path + '/rpms_control.json') as json_file:
            self.rpms_control_json = json.load(json_file)

        with open(full_path + '/rpms_test.json') as json_file:
            self.rpms_test_json = json.load(json_file)

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

        foo = [['2.8.08', '2.8.08-3.el8'], ['0', 'not installed']]
        bar = [['0', 'not installed'], ['2.8.08', '2.8.08-3.el8']]
        self.assertEqual(len(package_diff), 2)
        self.assertEqual(foo, package_diff['foo'])
        self.assertEqual(bar, package_diff['bar'])

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
