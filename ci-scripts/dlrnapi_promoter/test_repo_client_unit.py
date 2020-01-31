import csv
import os
import pytest
import shutil
import tempfile
import unittest

try:
    # Python3 imports
    from unittest.mock import Mock, patch
    import unittest.mock as mock
except ImportError:
    # Python2 imports
    from mock import Mock, patch
    import mock

from repo_client import RepoClient
from dlrn_hash import DlrnCommitDistroHash, DlrnAggregateHash
from config import PromoterConfigBase


class RepoSetup(unittest.TestCase):

    def setUp(self):
        self.dlrn_hash_commitdistro = DlrnCommitDistroHash(commit_hash='abc',
                                                           distro_hash='def',
                                                           component="comp1",
                                                           timestamp=1)
        self.dlrn_hash_commitdistro2 = DlrnCommitDistroHash(commit_hash='ghj',
                                                            distro_hash='klm',
                                                            component="comp2",
                                                            timestamp=2)
        self.dlrn_hash_aggregate = DlrnAggregateHash(commit_hash='abc',
                                                     distro_hash='def',
                                                     aggregate_hash='ghj',
                                                     timestamp=1)
        self.hashes = [self.dlrn_hash_commitdistro,
                       self.dlrn_hash_aggregate]
        self.temp_dir = tempfile.mkdtemp()
        self.versions_csv_dir = self.temp_dir
        config_defaults = PromoterConfigBase.defaults

        repo_url = "file://{}/".format(self.temp_dir)
        containers_list_base_url = "file://{}".format(self.temp_dir)
        config = type("Config", (), {
            'repo_url': repo_url,
            'containers_list_base_url': containers_list_base_url,
            'containers_list_path': config_defaults['containers_list_path']
        })
        self.client = RepoClient(config)
        fieldnames = ("Project,Source Repo,Source Sha,Dist Repo,Dist Sha,"
                      "Status,Last Success Timestamp,Component,Pkg NVR"
                      "").split(',')

        self.versions_csv_rows = [
            {
                'Project':
                    "python-tripleo-common-tests-tempest",
                'Source Repo':
                    "https://git.openstack.org/openstack/tripleo-common"
                    "-tempest-plugin",
                'Source Sha':
                    "f08b321392930b4255310b5aca8f704a32a79132",
                'Dist Repo':
                    "https://github.com/rdo-packages/tripleo-common-tempest"
                    "-plugin-distgit-git",
                'Dist Sha':
                    "7ae014d193ad00ddb5007431665a0b3347c2c94b",
                "Status": "SUCCESS",
                "Last Success Timestamp": "1580861715",
                "Component": "tripleo",
                "Pkg NVR":
                    "python-tripleo-common-tests-tempest-0.0.1-0.2020020500"
                    "1526.f08b321.el8"
            },
            {
                'Project': 'openstack-tripleo-common',
                'Source Repo':
                    "https://git.openstack.org/openstack/tripleo-common",
                'Source Sha':
                    "163d4b3b4b211358512fa9ee7f49d9fb930ecd8f",
                'Dist Repo':
                    "https://github.com/rdo-packages/tripleo-common-distgit"
                    "-git",
                'Dist Sha':
                    "22ed466781937e0506ad4afae0427338820c5601",
                "Status": "SUCCESS",
                "Last Success Timestamp": "1583519484",
                "Component": "tripleo",
                "Pkg NVR": "openstack-tripleo-common-12.1.1-0.20200306183249"
                           ".163d4b3"
                           ".el8"
            }
        ]

        # Create containers files
        containers_file_dirname = os.path.dirname(config_defaults[
                                                      'containers_list_path'])
        containers_dir = os.path.join(self.temp_dir,
                                      self.versions_csv_rows[1]['Source Sha'],
                                      containers_file_dirname)
        containers_list = ("{{name_prefix}}nova-api{{name_suffix}}\n"
                           "{{name_prefix}}neutron-server{{name_suffix}}\n")
        os.makedirs(containers_dir)
        containers_file_path = \
            os.path.join(containers_dir,
                         os.path.basename(config_defaults[
                                              'containers_list_path']))
        with open(containers_file_path, "w") as containers_file:
            containers_file.write(containers_list)

        # Crate empty containers file
        empty_containers_dir = os.path.join(self.temp_dir, "abc",
                                            containers_file_dirname)
        os.makedirs(empty_containers_dir)
        empty_containers_file_path = \
            os.path.join(empty_containers_dir,
                         os.path.basename(config_defaults[
                                              'containers_list_path']))
        with open(empty_containers_file_path, "w") as containers_file:
            pass

        # Create versions.csv files
        for dlrn_hash in self.hashes:
            dlrn_hash.label = "tripleo-ci-testing"
            versions_csv_dir = os.path.join(self.temp_dir,
                                            dlrn_hash.commit_dir)
            os.makedirs(versions_csv_dir)
            versions_csv_path = os.path.join(versions_csv_dir, "versions.csv")
            print(versions_csv_path)
            with open(versions_csv_path, "w") as versions_csv_file:
                csv_writer = csv.DictWriter(versions_csv_file,
                                            fieldnames=fieldnames)
                csv_writer.writeheader()
                for row in self.versions_csv_rows:
                    csv_writer.writerow(row)

    def tearDown(self):
        shutil.rmtree(self.versions_csv_dir)


class TestGetVersionsCsv(RepoSetup):

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    def test_get_version_csv_commitdistro_ok(self,
                                             mock_log_debug,
                                             mock_log_error):
        self.maxDiff = None
        out_versions_csv_reader =  \
            self.client.get_versions_csv(self.dlrn_hash_commitdistro,
                                         candidate_label="tripleo-ci-testing")

        self.assertIsInstance(out_versions_csv_reader, csv.DictReader)
        out_row = next(out_versions_csv_reader)
        self.assertEqual(out_row, self.versions_csv_rows[0])
        mock_log_debug.assert_has_calls([
            mock.call("Accessing versions at %s", mock.ANY)
        ])
        mock_log_error.assert_not_called()

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    def test_get_version_csv_aggregate_ok(self,
                                          mock_log_debug,
                                          mock_log_error):
        self.maxDiff = None
        out_versions_csv_reader = \
            self.client.get_versions_csv(self.dlrn_hash_aggregate,
                                         candidate_label="tripleo-ci-testing")

        out_row = next(out_versions_csv_reader)
        self.assertIsInstance(out_versions_csv_reader, csv.DictReader)
        self.assertEqual(out_row, self.versions_csv_rows[0])
        mock_log_debug.assert_has_calls([
            mock.call("Accessing versions at %s", mock.ANY)
        ])
        mock_log_error.assert_not_called()

    @patch('logging.Logger.exception')
    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    def test_get_version_csv_fail(self,
                                  mock_log_debug,
                                  mock_log_error,
                                  mock_log_exception):
        out_versions_csv_reader = \
            self.client.get_versions_csv(self.dlrn_hash_commitdistro2,
                                         candidate_label="tripleo-ci-testing")

        self.assertEqual(out_versions_csv_reader, None)
        mock_log_debug.assert_has_calls([
            mock.call("Accessing versions at %s", mock.ANY)
        ])
        mock_log_error.assert_has_calls([
            mock.call("Error downloading versions.csv file at %s", mock.ANY)
        ])
        self.assertTrue(mock_log_exception.called)


class TestGetContainersList(RepoSetup):

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    def test_get_commit_sha(self,
                            mock_log_debug,
                            mock_log_error):
        out_versions_csv_reader = \
            self.client.get_versions_csv(self.dlrn_hash_commitdistro,
                                         candidate_label="tripleo-ci-testing")
        tripleo_sha = self.client.get_commit_sha(out_versions_csv_reader,
                                                 "openstack-tripleo-common")
        self.assertEqual(tripleo_sha, self.versions_csv_rows[1]['Source Sha'])
        mock_log_debug.assert_has_calls([
            mock.call("Looking for sha commit of project %s in %s",
                      "openstack-tripleo-common", mock.ANY)
        ])
        mock_log_error.assert_not_called()

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    def test_get_commit_sha_failure(self,
                                    mock_log_debug,
                                    mock_log_error):
        out_versions_csv_reader = \
            self.client.get_versions_csv(self.dlrn_hash_commitdistro,
                                         candidate_label="tripleo-ci-testing")
        tripleo_sha = self.client.get_commit_sha(out_versions_csv_reader,
                                                 "nonexisting-project")
        self.assertEqual(tripleo_sha, None)
        mock_log_debug.assert_has_calls([
            mock.call("Looking for sha commit of project %s in %s",
                      "nonexisting-project", mock.ANY)
        ])
        mock_log_error.assert_has_calls([
            mock.call("Unable to find commit sha for project %s", mock.ANY)
        ])

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    def test_get_containers_list_ok(self,
                                    mock_log_debug,
                                    mock_log_error):
        containers_list = self.client.get_containers_list(
            self.versions_csv_rows[1]['Source Sha'])
        self.assertEqual(containers_list, ['nova-api', 'neutron-server'])
        mock_log_debug.assert_has_calls([
            mock.call("Attempting Download of containers template at %s",
                      mock.ANY)
        ])
        mock_log_error.assert_not_called()

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    def test_get_containers_list_fail_no_match(self,
                                               mock_log_debug,
                                               mock_log_error):
        containers_list = self.client.get_containers_list("abc")
        self.assertEqual(containers_list, [])
        mock_log_debug.assert_has_calls([
            mock.call("Attempting Download of containers template at %s",
                      mock.ANY)
        ])
        mock_log_error.assert_has_calls([
            mock.call("No containers name found in %s", mock.ANY)
        ])

    @patch('logging.Logger.exception')
    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    def test_get_containers_list_fail_containers_download(self,
                                                          mock_log_debug,
                                                          mock_log_error,
                                                          mock_log_exception):
        containers_list = self.client.get_containers_list("def")
        self.assertEqual(containers_list, [])
        mock_log_debug.assert_has_calls([
            mock.call("Attempting Download of containers template at %s",
                      mock.ANY)
        ])
        mock_log_error.assert_has_calls([
            mock.call("Unable to download containers template at %s", mock.ANY)
        ])
        self.assertTrue(mock_log_exception.called)
