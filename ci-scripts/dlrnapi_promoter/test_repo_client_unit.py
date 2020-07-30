import csv
import os
import shutil
import tempfile
import unittest

import yaml

try:
    # Python3 imports
    from unittest import mock
    from unittest.mock import patch
except ImportError:
    # Python2 imports
    from mock import patch
    import mock

from config_legacy import PromoterLegacyConfigBase
from dlrn_hash import DlrnAggregateHash, DlrnCommitDistroHash
from repo_client import RepoClient


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
                                                     aggregate_hash='ghjk',
                                                     timestamp=1)
        self.hashes = [self.dlrn_hash_commitdistro,
                       self.dlrn_hash_aggregate]
        self.temp_dir = tempfile.mkdtemp()
        self.versions_csv_dir = self.temp_dir
        config_defaults = PromoterLegacyConfigBase.defaults

        repo_url = "file://{}/".format(self.temp_dir)
        containers_list_base_url = "file://{}".format(self.temp_dir)
        containers_list_exclude_config_path = os.path.join(self.temp_dir,
                                                           "exclude_file.yaml")
        config = type("Config", (), {
            'repo_url': repo_url,
            'release': 'master',
            'build_method': 'kolla',
            'containers_list_base_url': containers_list_base_url,
            'containers_list_path': config_defaults['containers_list_path'],
            'containers_list_exclude_config': "file://{}".format(
                containers_list_exclude_config_path),
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
        # containers names coming from overcloud_containers.yaml file
        containers_list = """
container_images:
- image_source: kolla
  imagename: quay.io/tripleomaster/centos-binary-nova-api:current-tripleo
- image_source: kolla
  imagename: quay.io/tripleomaster/centos-binary-neutron-server:current-tripleo
- image_source: kolla
  imagename: quay.io/tripleomaster/centos-binary-excluded:current-tripleo
- image_source: kolla
  imagename: quay.io/tripleomaster/centos-binary-ovn-controller:current-tripleo
"""
        os.makedirs(containers_dir)
        containers_file_path = \
            os.path.join(containers_dir,
                         os.path.basename(config_defaults[
                                              'containers_list_path']))
        with open(containers_file_path, "w") as containers_file:
            containers_file.write(containers_list)

        # containers names coming from tripleo yaml file
        tripleo_containers_list = """
container_images:
- image_source: tripleo
  imagename: quay.io/tripleomaster/openstack-base:current-tripleo
- image_source: tripleo
  imagename: quay.io/tripleomaster/openstack-os:current-tripleo
- image_source: tripleo
  imagename: quay.io/tripleomaster/openstack-aodh-base:current-tripleo
"""
        tripleo_containers_file_path = \
            os.path.join(containers_dir, 'tripleo_containers.yaml')
        with open(tripleo_containers_file_path, "w") as containers_file:
            containers_file.write(tripleo_containers_list)

        # containers names coming from yaml file for queens release
        tripleo_containers_list = """
container_images:
- imagename: quay.io/tripleomaster/centos-binary-base:current-tripleo
- imagename: quay.io/tripleomaster/centos-binary-os:current-tripleo
- imagename: quay.io/tripleomaster/centos-binary-aodh-base:current-tripleo
"""
        overcloud_containers_file_path = \
            os.path.join(containers_dir, 'queens_containers.yaml')
        with open(overcloud_containers_file_path, "w") as containers_file:
            containers_file.write(tripleo_containers_list)

        # create exclude config

        excluded_containers = ['nonexisting', 'excluded']
        exclude_config = {
            'exclude_containers': {
                'master': excluded_containers,
            },
        }
        with open(containers_list_exclude_config_path, "w") as exclude_file:
            exclude_file.write(yaml.safe_dump(exclude_config))

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

        self.assertNotEqual(out_versions_csv_reader, None)
        self.assertIsInstance(out_versions_csv_reader, csv.DictReader)
        out_row = next(out_versions_csv_reader)
        self.assertEqual(out_row, self.versions_csv_rows[0])
        mock_log_debug.assert_has_calls([
            mock.call("Accessing versions at %s", mock.ANY)
        ])
        self.assertFalse(mock_log_error.called)

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    def test_get_version_csv_aggregate_ok(self,
                                          mock_log_debug,
                                          mock_log_error):
        self.maxDiff = None
        out_versions_csv_reader = \
            self.client.get_versions_csv(self.dlrn_hash_aggregate,
                                         candidate_label="tripleo-ci-testing")

        self.assertNotEqual(out_versions_csv_reader, None)
        out_row = next(out_versions_csv_reader)
        self.assertIsInstance(out_versions_csv_reader, csv.DictReader)
        self.assertEqual(out_row, self.versions_csv_rows[0])
        mock_log_debug.assert_has_calls([
            mock.call("Accessing versions at %s", mock.ANY)
        ])
        self.assertFalse(mock_log_error.called)

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
        self.assertFalse(mock_log_error.called)

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
    def test_get_containers_list_overcloud(self,
                                           mock_log_debug,
                                           mock_log_error):
        self.client.build_method = "kolla"
        containers_list = self.client.get_containers_list(
            self.versions_csv_rows[1]['Source Sha'])
        self.assertEqual(containers_list, ['nova-api', 'neutron-server',
                                           'ovn-controller'])
        mock_log_debug.assert_has_calls([
            mock.call("Attempting Download of containers template at %s",
                      mock.ANY)
        ])
        self.assertFalse(mock_log_error.called)

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    def test_get_containers_list_tripleo(self,
                                         mock_log_debug,
                                         mock_log_error):
        self.client.build_method = "tripleo"
        self.client.release = "foobar"
        self.client.containers_list_path = (
                'container-images/tripleo_containers.yaml'
        )
        containers_list = self.client.get_containers_list(
            self.versions_csv_rows[1]['Source Sha'])
        self.assertEqual(containers_list, ['base', 'os', 'aodh-base'])
        mock_log_debug.assert_has_calls([
            mock.call("Attempting Download of containers template at %s",
                      mock.ANY)
        ])
        mock_log_error.assert_not_called()

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    def test_get_containers_list_queens(self,
                                        mock_log_debug,
                                        mock_log_error):
        self.client.release = "queens"
        self.client.containers_list_path = (
                'container-images/queens_containers.yaml'
        )
        containers_list = self.client.get_containers_list(
            self.versions_csv_rows[1]['Source Sha'])
        self.assertEqual(containers_list, ['base', 'os', 'aodh-base'])
        mock_log_debug.assert_has_calls([
            mock.call("Attempting Download of containers template at %s",
                      mock.ANY)
        ])
        mock_log_error.assert_not_called()

    @patch('logging.Logger.error')
    @patch('logging.Logger.debug')
    def test_get_containers_list_ok_no_excludes(self,
                                                mock_log_debug,
                                                mock_log_error):
        containers_list = self.client.get_containers_list(
            self.versions_csv_rows[1]['Source Sha'], load_excludes=False)
        self.assertEqual(containers_list, ['nova-api', 'neutron-server',
                                           'excluded', 'ovn-controller'])
        mock_log_debug.assert_has_calls([
            mock.call("Attempting Download of containers template at %s",
                      mock.ANY)
        ])
        self.assertFalse(mock_log_error.called)

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

    @patch('logging.Logger.debug')
    @patch('logging.Logger.exception')
    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    def test_load_excludes_correct(self,
                                   mock_log_info,
                                   mock_log_error,
                                   mock_log_exception,
                                   mock_log_debug):
        input_full_list = ['nova-api', 'neutron-server', 'excluded']
        expect_full_list = ['nova-api', 'neutron-server']
        full_list = self.client.load_excludes(input_full_list)
        self.assertEqual(full_list, expect_full_list)

        mock_log_info.assert_has_calls([
            mock.call("Excluding %s from the containers list",
                      'excluded')
        ])
        mock_log_debug.assert_has_calls([
            mock.call("%s not in containers list", 'nonexisting')
        ])
        self.assertFalse(mock_log_error.called)
        self.assertFalse(mock_log_exception.called)

    @patch('logging.Logger.warning')
    @patch('logging.Logger.debug')
    @patch('logging.Logger.exception')
    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    def test_load_excludes_file_not_found(self,
                                          mock_log_info,
                                          mock_log_error,
                                          mock_log_exception,
                                          mock_log_debug,
                                          mock_log_warning):
        self.client.containers_list_exclude_config = 'file:///not/existing'
        input_full_list = ['nova-api', 'neutron-server', 'excluded']
        full_list = self.client.load_excludes(input_full_list)
        self.assertEqual(full_list, input_full_list)

        mock_log_warning.assert_has_calls([
            mock.call('Unable to download containers exclude config at %s, '
                      'no exclusion',
                      self.client.containers_list_exclude_config)
        ])

        self.assertTrue(mock_log_exception.called)
        self.assertFalse(mock_log_error.called)
        self.assertFalse(mock_log_info.called)
        self.assertFalse(mock_log_debug.called)

    @patch('logging.Logger.warning')
    @patch('logging.Logger.debug')
    @patch('logging.Logger.exception')
    @patch('logging.Logger.error')
    @patch('logging.Logger.info')
    def test_load_excludes_distro_not_found(self,
                                            mock_log_info,
                                            mock_log_error,
                                            mock_log_exception,
                                            mock_log_debug,
                                            mock_log_warning):
        self.client.release = 'ussuri'
        input_full_list = ['nova-api', 'neutron-server', 'excluded']
        full_list = self.client.load_excludes(input_full_list)
        self.assertEqual(full_list, input_full_list)

        mock_log_warning.assert_has_calls([
            mock.call('Unable to find container exclude list for %s', 'ussuri')
        ])

        self.assertFalse(mock_log_error.called)
        self.assertFalse(mock_log_info.called)
        self.assertFalse(mock_log_debug.called)
        self.assertFalse(mock_log_exception.called)
