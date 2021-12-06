import unittest

import node_holder


class TestNodeHolder(unittest.TestCase):
    def test_fetch_change_id_postive_test(self):
        url = ('https://review.rdoproject.org/r/c/testproject/'
               '+/28446/63/.zuul.yaml')
        self.assertEqual(node_holder.fetch_change_id(url), '28446')

    def test_fetch_change_id_negative_test(self):
        with self.assertRaises(AttributeError):
            node_holder.fetch_change_id(
                'https://review.rdoproject.org/r/c/testproject/+/')

    def test_fetch_patchset_number_postive_test(self):
        url = ('https://review.rdoproject.org/r/c/testproject'
               '/+/28446/63/.zuul.yaml')
        self.assertEqual(
            node_holder.fetch_patchset_number(url), '63')

    def test_fetch_patchset_number_negative_test(self):
        with self.assertRaises(IndexError):
            node_holder.fetch_patchset_number(
                'https://review.rdoproject.org/r/c/testproject/+/')

    def test_fetch_project_name_positive_test(self):
        url = ('https://review.rdoproject.org/r/c/testproject'
               '/+/28446/63/.zuul.yaml')
        self.assertEqual(node_holder.fetch_project_name(url), 'testproject')

    def test_fetch_project_name_positive_test_something_before_project(self):
        self.assertEqual(node_holder.fetch_project_name(
            'https://review.opendev.org/c/openstack/tripleo-ci/+/706288/'),
            'tripleo-ci')
        self.assertEqual(node_holder.fetch_project_name(
            'https://review.rdoproject.org/r/c/rdo-infra/ci-config/+/36911'),
            'ci-config')

    def test_fetch_project_name_negative_test(self):
        with self.assertRaises(IndexError):
            node_holder.fetch_project_name(
                'https://review.rdoproject.org/r/c/')

    def test_gerrit_check_postive(self):
        url = ('https://review.rdoproject.org/r/c/testproject'
               '/+/28446/63/.zuul.yaml')
        self.assertEqual(node_holder.gerrit_check(url), 'rdo')
        self.assertEqual(node_holder.gerrit_check(
            'https://review.opendev.org/c/openstack/tripleo-ci/+/706288/'),
            'upstream')

    def test_gerrit_check_negative(self):
        with self.assertRaises(Exception):
            node_holder.gerrit_check('https://google.com')

    def test_fetch_file_name_postive_test(self):
        url = ('https://review.rdoproject.org/r/c/testproject'
               '/+/28446/63/.zuul.yaml')
        url2 = ('https://review.rdoproject.org/r/c/rdo-jobs/+/'
                '37139/1/zuul.d/projects.yaml')
        self.assertEqual(node_holder.fetch_file_name(url), '.zuul.yaml')
        self.assertEqual(node_holder.fetch_file_name(
            url2), 'zuul.d%2Fprojects.yaml')

    def test_fetch_file_name_negative_test(self):
        with self.assertRaises(Exception):
            node_holder.fetch_file_name(
                'https://review.rdoproject.org/r/c/testproject/')

    def test_convert_patch_url_to_download_url_postive_test(self):
        url = ('https://review.rdoproject.org/r/c/testproject'
               '/+/28446/63/.zuul.yaml')
        expected = ("https://review.rdoproject.org/r/changes/testproject~"
                    "28446/revisions/63/files/.zuul.yaml/download")
        self.assertEqual(node_holder.convert_patch_url_to_download_url(
            url, '28446', 'testproject', '63', '.zuul.yaml'),
            expected)

    def test_convert_patch_url_to_download_url_n_test_c_not_present(self):
        url1 = ('https://review.rdoproject.org/r/testproject'
                '/+/28446/63/.zuul.yaml')
        with self.assertRaises(Exception):
            node_holder.convert_patch_url_to_download_url(
                url1, '28446', 'testproject', '63', '.zuul.yaml')
