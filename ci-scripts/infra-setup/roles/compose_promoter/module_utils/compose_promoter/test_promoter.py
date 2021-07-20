import unittest
import urllib.request
from unittest import mock

import ddt
import paramiko

from . import promoter


class TestComposePromoterBase(unittest.TestCase):

    def mock_object(self, obj, attr, new_attr=None):
        if not new_attr:
            new_attr = mock.Mock()

        patcher = mock.patch.object(obj, attr, new_attr)
        patcher.start()
        # stop patcher at the end of the test
        self.addCleanup(patcher.stop)

        return new_attr


class TestComposePromoterSftpClient(TestComposePromoterBase):

    def test_sftp_client_connect_get_attr_close(self):
        fake_hostname = 'fake_host'
        fake_user = 'fake_user'
        fake_port = 22222
        fake_key_path = '/path/to/fake_key'
        fake_pass = 'fake_password'

        ssh_client_mock = mock.Mock()
        sftp_client_mock = mock.Mock()
        pkey_mock = mock.Mock()
        self.mock_object(paramiko, 'SSHClient',
                         mock.Mock(return_value=ssh_client_mock))
        self.mock_object(paramiko, 'AutoAddPolicy')
        mock_from_pkey = self.mock_object(
            paramiko.RSAKey, 'from_private_key_file',
            mock.Mock(return_value=pkey_mock))
        mock_connect = self.mock_object(ssh_client_mock, 'connect')
        mock_open_sftp = self.mock_object(
            ssh_client_mock, 'open_sftp',
            mock.Mock(return_value=sftp_client_mock))
        mock_fake_op = self.mock_object(sftp_client_mock, 'fake_operation')
        mock_close_sftp = self.mock_object(sftp_client_mock, 'close')

        client = promoter.SftpClient(
            hostname=fake_hostname, user=fake_user, pkey_path=fake_key_path,
            port=fake_port, password=fake_pass
        )

        # connect
        client.connect()
        # get_attr
        client.fake_operation()
        # close
        client.close()

        mock_from_pkey.assert_called_once_with(filename=fake_key_path)
        mock_connect.assert_called_once_with(
            fake_hostname, port=fake_port, username=fake_user,
            password=fake_pass, pkey=pkey_mock
        )
        mock_open_sftp.assert_called_once()
        mock_fake_op.assert_called_once()
        mock_close_sftp.assert_called_once()


@ddt.ddt
class TestComposePromoter(TestComposePromoterBase):

    def setUp(self):
        super(TestComposePromoter, self).setUp()
        self.client_mock = mock.Mock()
        self.fake_work_dir = '/path/to/work_dir'
        self.fake_url = 'fake_compose_url'
        self.fake_distro = 'fake-distro'

        self.promoter = promoter.ComposePromoter(
            self.client_mock, self.fake_work_dir,
            self.fake_distro, self.fake_url
        )

    def test_retrieve_latest_compose(self):
        fake_compose_id = 'fake_compose_id'
        urlopen_mock = mock.Mock()
        readline_mock = mock.Mock()
        urlopen_method = self.mock_object(
            urllib.request, 'urlopen',
            mock.Mock(return_value=urlopen_mock))
        self.mock_object(urlopen_mock, 'readline',
                         mock.Mock(return_value=readline_mock))
        self.mock_object(readline_mock, 'decode',
                         mock.Mock(return_value=fake_compose_id))

        result = self.promoter.retrieve_latest_compose()

        self.assertEqual(fake_compose_id, result)
        urlopen_method.assert_called_once_with(self.fake_url)

    def test_retrieve_latest_compose_exception(self):
        self.mock_object(urllib.request, 'urlopen',
                         mock.Mock(side_effect=Exception))

        self.assertRaises(
            promoter.ComposePromoterError,
            self.promoter.retrieve_latest_compose
        )

    @ddt.data(
        {'candidate': 'latest-compose',
         'target': 'tripleo-ci-testing',
         'exp_result': True},

        {'candidate': 'tripleo-ci-testing',
         'target': 'current-tripleo',
         'exp_result': False},
    )
    @ddt.unpack
    def test_validate(self, candidate, target, exp_result):
        result = self.promoter.validate(target, candidate_label=candidate)

        self.assertEqual(exp_result, result)

    def test_rollback(self):
        fake_files = ['file1', 'file2']
        fake_links = {'target_label': 'previous_file'}
        remove_mock = self.mock_object(self.promoter.client, 'remove')
        unlink_mock = self.mock_object(self.promoter.client, 'unlink')
        symlink_mock = self.mock_object(self.promoter.client, 'symlink')

        self.promoter.rollback(remove_files=fake_files,
                               previous_links=fake_links)

        remove_calls = [mock.call(file) for file in fake_files]
        remove_mock.assert_has_calls(remove_calls)
        unlink_calls = [mock.call(key) for key in fake_links]
        unlink_mock.assert_has_calls(unlink_calls)
        symlink_calls = [mock.call(v, k) for k, v in fake_links.items()]
        symlink_mock.assert_has_calls(symlink_calls)

    def test_promote(self):
        fake_target_label = 'target_label'
        fake_candidate_label = 'candidate_label'
        connect_mock = self.mock_object(self.promoter.client, 'connect')
        validate_mock = self.mock_object(self.promoter, 'validate',
                                         mock.Mock(return_value=True))
        promote_latest_mock = self.mock_object(self.promoter,
                                               'promote_latest_compose')
        close_mock = self.mock_object(self.promoter.client, 'close')

        self.promoter.promote(fake_target_label,
                              candidate_label=fake_candidate_label)

        connect_mock.assert_called_once()
        validate_mock.assert_called_once_with(
            fake_target_label, candidate_label=fake_candidate_label)
        promote_latest_mock.assert_called_once_with(fake_target_label)
        close_mock.assert_called_once()

    def test_promote_invalid_label(self):
        fake_target_label = 'target_label'
        fake_candidate_label = 'candidate_label'
        validate_mock = self.mock_object(self.promoter, 'validate',
                                         mock.Mock(return_value=False))

        self.assertRaises(promoter.ComposePromoterError,
                          self.promoter.promote,
                          fake_target_label,
                          candidate_label=fake_candidate_label)

        validate_mock.assert_called_once_with(
            fake_target_label, candidate_label=fake_candidate_label)

    def test_promote_invalid_working_dir(self):
        fake_target_label = 'target_label'
        fake_candidate_label = 'candidate_label'
        connect_mock = self.mock_object(self.promoter.client, 'connect')
        validate_mock = self.mock_object(self.promoter, 'validate',
                                         mock.Mock(return_value=True))
        listdir_mock = self.mock_object(
            self.promoter.client, 'listdir',
            mock.Mock(side_effect=FileNotFoundError))
        close_mock = self.mock_object(self.promoter.client, 'close')

        self.assertRaises(promoter.ComposePromoterError,
                          self.promoter.promote,
                          fake_target_label,
                          candidate_label=fake_candidate_label)

        connect_mock.assert_called_once()
        listdir_mock.assert_called_once_with(self.promoter.working_dir)
        validate_mock.assert_called_once_with(
            fake_target_label, candidate_label=fake_candidate_label)
        close_mock.assert_called_once()

    def test_promote_promotion_error(self):
        fake_target_label = 'target_label'
        fake_candidate_label = 'candidate_label'
        connect_mock = self.mock_object(self.promoter.client, 'connect')
        validate_mock = self.mock_object(self.promoter, 'validate',
                                         mock.Mock(return_value=True))
        promote_latest_mock = self.mock_object(
            self.promoter, 'promote_latest_compose',
            mock.Mock(side_effect=promoter.ComposePromoterError))
        close_mock = self.mock_object(self.promoter.client, 'close')

        self.assertRaises(promoter.ComposePromoterError,
                          self.promoter.promote,
                          fake_target_label,
                          candidate_label=fake_candidate_label)

        connect_mock.assert_called_once()
        promote_latest_mock.assert_called_once_with(fake_target_label)
        validate_mock.assert_called_once_with(
            fake_target_label, candidate_label=fake_candidate_label)
        close_mock.assert_called_once()

    @ddt.data(False, True)
    def test_promote_latest_compose(self, same_as_current):
        fake_compose_id = 'fake_compose_id'
        fake_old_compose_id = (
            fake_compose_id if same_as_current else 'fake_compose_id_2')
        fake_target_label = 'fake_target_label'
        retrieve_mock = self.mock_object(
            self.promoter, 'retrieve_latest_compose',
            mock.Mock(return_value=fake_compose_id))
        stat_mock = self.mock_object(self.promoter.client, 'stat',
                                     mock.Mock(return_value=None))
        file_mock = self.mock_object(self.promoter.client, 'file')
        unlink_mock = self.mock_object(self.promoter.client, 'unlink')
        symlink_mock = self.mock_object(self.promoter.client, 'symlink')

        readlink_mock = self.mock_object(
            self.promoter.client, 'readlink',
            mock.Mock(return_value=fake_old_compose_id))

        self.promoter.promote_latest_compose(fake_target_label)

        retrieve_mock.assert_called_once()
        stat_mock.assert_called_once_with(fake_compose_id)
        file_mock.assert_called_once_with(fake_compose_id, mode='w')
        readlink_mock.assert_called_once_with(fake_target_label)
        if not same_as_current:
            unlink_mock.assert_called_once_with(fake_target_label)
            symlink_mock.assert_called_once_with(fake_compose_id,
                                                 fake_target_label)

    @ddt.data('stat', 'file', 'unlink', 'symlink')
    def test_promote_latest_compose_error(self, failed_op):
        fake_compose_id = 'fake_compose_id'
        fake_old_compose_id = 'fake_old_compose_id'
        fake_target_label = 'fake_target_label'
        excep_mock = mock.Mock(side_effect=EnvironmentError)

        retrieve_mock = self.mock_object(
            self.promoter, 'retrieve_latest_compose',
            mock.Mock(return_value=fake_compose_id))

        stat_mock_res = excep_mock if failed_op == 'stat' else mock.Mock(
            return_value=None)
        self.mock_object(self.promoter.client, 'stat', stat_mock_res)

        file_mock_res = excep_mock if failed_op == 'file' else mock.Mock()
        self.mock_object(self.promoter.client, 'file', file_mock_res)

        unlink_mock_res = excep_mock if failed_op == 'unlink' else mock.Mock()
        self.mock_object(self.promoter.client, 'unlink', unlink_mock_res)

        slink_mock_res = excep_mock if failed_op == 'symlink' else mock.Mock()
        self.mock_object(self.promoter.client, 'symlink', slink_mock_res)

        self.mock_object(self.promoter.client, 'readlink',
                         mock.Mock(return_value=fake_old_compose_id))
        rollback_mock = self.mock_object(self.promoter, 'rollback')

        self.assertRaises(promoter.ComposePromoterError,
                          self.promoter.promote_latest_compose,
                          fake_target_label)

        retrieve_mock.assert_called_once()
        if failed_op == 'unlink':
            rollback_mock.assert_called_once_with(
                remove_files=[fake_compose_id])
        if failed_op == 'symlink':
            rollback_mock.assert_called_once_with(
                remove_files=[fake_compose_id],
                previous_links={fake_target_label: fake_old_compose_id}
            )


if __name__ == '__main__':
    unittest.main()
