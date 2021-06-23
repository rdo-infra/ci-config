#! /usr/bin/python3
""" Unit test for ovb_tenant_cleanup.py """
import datetime
import unittest
from unittest import mock

import openstack
import ovb_tenant_cleanup


class TestCleanupScript(unittest.TestCase):
    """ Class to test functions in ovb_tenant_cleanup script which
        don't require mock
    """

    def test_remove_prefix(self):
        """ Unit test for remove_prefix function """
        obtained = ovb_tenant_cleanup.remove_prefix(
                       "baremetal_763542_36_39000",
                       "baremetal_")
        expected = "763542_36_39000"
        self.assertEqual(obtained, expected)

    def test_remove_suffix(self):
        """ Unit test for remove_suffix function """
        obtained = ovb_tenant_cleanup.remove_suffix(
                       "baremetal_763542_36_39000",
                       "")
        expected = "baremetal_763542_36_39000"

        self.assertEqual(obtained, expected)
        obtained = ovb_tenant_cleanup.remove_suffix(
                       "763542_36_39000-extra",
                       "-extra")
        expected = "763542_36_39000"
        self.assertEqual(obtained, expected)

    def test_fetch_identifier(self):
        """ Unit test for fetch_identifier function """
        obtained = ovb_tenant_cleanup.fetch_identifier(
                       "baremetal_763542_36_39000",
                       "baremetal_",
                       "")
        expected = "763542_36_39000"
        self.assertEqual(obtained, expected)

        obtained = ovb_tenant_cleanup.fetch_identifier(
                       "baremetal_763542_36_39000-extra",
                       "baremetal_",
                       "-extra")
        expected = "763542_36_39000"
        self.assertEqual(obtained, expected)


@mock.patch('openstack.connect', autospec=True)
@mock.patch.object(openstack.connection, 'Connection', autospec=True)
class CloudResourcesTest(unittest.TestCase):
    """ Class to test cloud resource fetch functions in ovb_tenant_cleanup
        script which requires similiar mocks for openstack.connect.
    """

    mocked_server_list = [
        openstack.compute.v2.server.Server(
            id='48157f70-238e-4452-9ddf-9415ada358dd', name='vm',
            addresses={'ctlplane-73303': [{'version': 4}]}),
        openstack.compute.v2.server.Server(
            id='2f8b5478-dc19-49ce-8421-62b87bcb8b35', name='public-73303',
            addresses={'private': [{'version': 4}]}),
        openstack.compute.v2.server.Server(
            id='b04d0ec1-5f95-480d-a1b2-e47d0929b706', name='public-43666',
            addresses={'private': [{'version': 4}]}),
        openstack.compute.v2.server.Server(
            id='04457b87-441d-4f9c-8e2e-d7bed3db3473', name='vm05',
            addresses={'ctlplane-32495': [{'version': 4}]})]

    mocked_subnet_list = [
        openstack.network.v2.subnet.Subnet(
            id='48e016af-15fb-4e5a-904f-66857280188f', name='private_subnet'),
        openstack.network.v2.subnet.Subnet(
            id='a1742089-430d-444e-a7ae-41f81270fac3', name='ctlplane-73303'),
        openstack.network.v2.subnet.Subnet(
            id='acafabb8-d420-43fd-bf99-11977139b4cf', name='ctlplane-32495')]

    mocked_network_list = [
        openstack.network.v2.network.Network(
            id='2e3b285a-4ac7-42c3-af3e-073dc7c26494', name='ctlplane-32495'),
        openstack.network.v2.network.Network(
            id='448833ff-46bb-4689-841e-f965340af45d', name='ctlplane-73303'),
        openstack.network.v2.network.Network(
            id='7c4efd32-3210-4ed0-9d49-748960faf29f', name='private')]

    mocked_port_list = [
        openstack.network.v2.port.Port(
            id='141caeef-7813-45a8-831c-db747ed6d5d6',
            fixed_ips=[
                {'subnet_id': 'a1742089-430d-444e-a7ae-41f81270fac3',
                 'ip_address': '192.168.20.2'}]),
        openstack.network.v2.port.Port(
            id='4204ffbb-ef7e-43bf-8479-333e4f37040a',
            fixed_ips=[
                {'subnet_id': 'a1742089-430d-444e-a7ae-41f81270fac3',
                 'ip_address': '192.168.20.9'}])]

    mocked_router_list = [
        openstack.network.v2.router.Router(
            id='6bd7055f-8d5f-4656-b6b1-a1679faa1c91',
            name='baremetal_73303-private_network-router-v4an5n2frvtf'),
        openstack.network.v2.router.Router(
            id='95c3762a-f7ef-4b48-b856-2e9b02e54e44',
            name='router-test')]

    mocked_security_group_list = [
        openstack.network.v2.security_group.SecurityGroup(
            id='1f5af4ed-e54d-4774-9299-3ac5fa2c5cd3',
            name='extranode_baremetal-73303-extra__0_sg'),
        openstack.network.v2.security_group.SecurityGroup(
            id='6684e2e0-c112-4e8c-8dc1-6973ee98cf7e',
            name='default')]

    def test_env_accessibility_check_when_cloud_reachable(self, mock_conn,
                                                          mock_connect):
        """ Positive test for env_accessibility_check function """
        mock_connect.return_value = mock_conn
        mock_conn.identity.get_token.return_value = 'gAA123'
        self.assertTrue(
                ovb_tenant_cleanup.env_accessibility_check('testcloud'))

    def test_env_accessibility_check_when_cloud_unreachable(self, mock_conn,
                                                            mock_connect):
        """ Negative test for env_accessibility_check function """
        mock_connect.return_value = mock_conn
        mock_conn.identity.get_token.side_effect = Exception(
                'Unable to reach cloud!')
        self.assertFalse(
                ovb_tenant_cleanup.env_accessibility_check('testcloud'))

    def test_servers_when_identifier_is_73303(self, mock_conn, mock_connect):
        """ Positive test for servers_with_identifier function """
        mock_connect.return_value = mock_conn
        mock_conn.compute.servers.return_value = iter(self.mocked_server_list)
        self.assertEqual(ovb_tenant_cleanup.servers_with_identifier(
                         'testcloud', '73303'),
                         ['48157f70-238e-4452-9ddf-9415ada358dd',
                          '2f8b5478-dc19-49ce-8421-62b87bcb8b35'])

    def test_servers_when_identifier_is_43666(self, mock_conn, mock_connect):
        """ Positive test for servers_with_identifier function """
        mock_connect.return_value = mock_conn
        mock_conn.compute.servers.return_value = iter(self.mocked_server_list)
        self.assertEqual(ovb_tenant_cleanup.servers_with_identifier(
                         'testcloud', '43666'),
                         ['b04d0ec1-5f95-480d-a1b2-e47d0929b706'])

    def test_servers_when_identifier_is_123456_negative_test(self, mock_conn,
                                                             mock_connect):
        """ Negative test for servers_with_identifier function """
        mock_connect.return_value = mock_conn
        mock_conn.compute.servers.return_value = iter(self.mocked_server_list)
        self.assertEqual(ovb_tenant_cleanup.servers_with_identifier(
                         'testcloud', '123456'), [])

    def test_subnet_when_identifier_is_73303(self, mock_conn, mock_connect):
        """ Positive test for subnet_with_identifier function """
        mock_connect.return_value = mock_conn
        mock_conn.network.subnets.return_value = iter(self.mocked_subnet_list)
        self.assertEqual(ovb_tenant_cleanup.subnets_with_identifier(
                         'testcloud', '73303'),
                         ['a1742089-430d-444e-a7ae-41f81270fac3'])

    def test_subnet_when_identifier_is_123456_negative_test(self, mock_conn,
                                                            mock_connect):
        """ Negative test for subnet_with_identifier function """
        mock_connect.return_value = mock_conn
        mock_conn.network.subnets.return_value = iter(self.mocked_subnet_list)
        self.assertEqual(ovb_tenant_cleanup.subnets_with_identifier(
                         'testcloud', '123456'), [])

    def test_network_when_identifier_is_73303(self, mock_conn, mock_connect):
        """ Positive test for network_with_identifier function """
        mock_connect.return_value = mock_conn
        mock_conn.network.networks.return_value = iter(
                self.mocked_network_list)
        self.assertEqual(ovb_tenant_cleanup.networks_with_identifier(
                         'testcloud', '73303'),
                         ['448833ff-46bb-4689-841e-f965340af45d'])

    def test_network_when_identifier_is_123456_negative_test(self, mock_conn,
                                                             mock_connect):
        """ Negative test for negative_with_identifier function """
        mock_connect.return_value = mock_conn
        mock_conn.network.networks.return_value = iter(
                self.mocked_network_list)
        self.assertEqual(ovb_tenant_cleanup.networks_with_identifier(
                         "testcloud", "123456"), [])

    def test_port_when_subnet_id_given(self, mock_conn, mock_connect):
        """ Positive test for ports_of_subnet function """
        mock_connect.return_value = mock_conn
        mock_conn.network.get_subnet_ports.return_value = iter(
                self.mocked_port_list)
        self.assertEqual(ovb_tenant_cleanup.ports_of_subnets(
            "testcloud", "a1742089-430d-444e-a7ae-41f81270fac3"),
            ['141caeef-7813-45a8-831c-db747ed6d5d6',
             '4204ffbb-ef7e-43bf-8479-333e4f37040a'])

    def test_port_when_subnet_id_is_none_negative_test(self, mock_conn,
                                                       mock_connect):
        """ Negative test for ports_of_subnet function """
        mock_connect.return_value = mock_conn
        mock_conn.network.get_subnet_ports.return_value = iter(
                self.mocked_port_list)
        self.assertEqual(ovb_tenant_cleanup.ports_of_subnets(
                         "testcloud", None), [])

    def test_router_when_identifier_is_73303(self, mock_conn, mock_connect):
        """ Positive test for ports_of_subnet function """
        mock_connect.return_value = mock_conn
        mock_conn.network.routers.return_value = iter(self.mocked_router_list)
        self.assertEqual(ovb_tenant_cleanup.routers_with_identifier(
                         "testcloud", "73303"),
                         ['6bd7055f-8d5f-4656-b6b1-a1679faa1c91'])

    def test_router_when_identifier_is_123456_negative_test(self, mock_conn,
                                                            mock_connect):
        """ Negative test for ports_of_subnet function """
        mock_connect.return_value = mock_conn
        mock_conn.network.routers.return_value = iter(self.mocked_router_list)
        self.assertEqual(ovb_tenant_cleanup.routers_with_identifier(
                         "testcloud", "123456"), [])

    def test_sec_gp_when_identifier_is_73303(self, mock_conn, mock_connect):
        """ Positive test for sec_gp_with_identifier function """
        mock_connect.return_value = mock_conn
        mock_conn.network.security_groups.return_value = iter(
                self.mocked_security_group_list)
        self.assertEqual(ovb_tenant_cleanup.sec_gp_with_identifier(
                         "testcloud", "73303"),
                         ['1f5af4ed-e54d-4774-9299-3ac5fa2c5cd3'])

    def test_sec_gp_when_identifier_is_123456_negative_test(self, mock_conn,
                                                            mock_connect):
        """ Negative test for sec_gp_with_identifier function """
        mock_connect.return_value = mock_conn
        mock_conn.network.security_groups.return_value = iter(
                self.mocked_security_group_list)
        self.assertEqual(ovb_tenant_cleanup.sec_gp_with_identifier(
                         "testcloud", "123456"), [])


class HeatTests(unittest.TestCase):
    """ Class to test Heat Stack realted functions in ovb_tenant_cleanup
        script which requires similiar mocks for openstack.connect and
        datetime.
    """
    mocked_heat_stacks = [
        openstack.orchestration.v1.stack.Stack(
            id='9098d9d4-70e9-4802-8412-dff7c898ba50',
            stack_name='baremetal_73703',
            stack_status='DELETE_FAILED',
            creation_time='2021-04-04T20:05:19Z',
            tags=None),
        openstack.orchestration.v1.stack.Stack(
            id='410f6f7e-e778-4a78-9db5-8a58d33b178f',
            stack_name='baremetal_43666',
            stack_status='CREATE_COMPLETE',
            creation_time='2021-04-04T18:04:17Z',
            tags=None),
        openstack.orchestration.v1.stack.Stack(
            id='39ce9687-0c9a-463f-b4c1-2d30f082f3cf',
            stack_name='baremetal_123456',
            stack_status='DELETE_IN_PROGRESS',
            creation_time='2021-04-04T23:05:17Z',
            tags=None)]

    def setUp(self):
        self.mock_conn_patcher = mock.patch.object(openstack.connection,
                                                   'Connection', autospec=True)
        self.mock_connect_patcher = mock.patch('openstack.connect',
                                               autospec=True)
        self.mock_date_patcher = mock.patch('ovb_tenant_cleanup.datetime')

        self.mock_conn = self.mock_conn_patcher.start()
        self.mock_connect = self.mock_connect_patcher.start()
        self.mock_date = self.mock_date_patcher.start()

        self.mock_connect.return_value = self.mock_conn
        olddate = datetime.datetime(2021, 4, 5)
        self.mock_date.datetime.now.return_value = olddate.replace(
                tzinfo=datetime.timezone.utc)
        self.mock_conn.orchestration.stacks.return_value = iter(
                self.mocked_heat_stacks)

    def tearDown(self):
        self.mock_conn_patcher.stop()
        self.mock_connect_patcher.stop()
        self.mock_date_patcher.stop()

    def test_old_heat_stacks_time_expired_5_hours(self):
        """ Unit test for old_heat_stacks function """
        self.mock_date.timedelta.return_value = datetime.timedelta(minutes=300)
        self.assertEqual(ovb_tenant_cleanup.old_heat_stacks('testcloud'),
                         ['410f6f7e-e778-4a78-9db5-8a58d33b178f'])

    def test_old_heat_stacks_time_expired_2_hours(self):
        """ Unit test for old_heat_stacks function """
        self.mock_date.timedelta.return_value = datetime.timedelta(minutes=120)
        self.assertEqual(ovb_tenant_cleanup.old_heat_stacks('testcloud'),
                         ['9098d9d4-70e9-4802-8412-dff7c898ba50',
                         '410f6f7e-e778-4a78-9db5-8a58d33b178f'])

    def test_old_heat_stacks_time_expired_10_hours(self):
        """ Unit test for old_heat_stacks function """
        self.mock_date.timedelta.return_value = datetime.timedelta(minutes=600)
        self.assertEqual(ovb_tenant_cleanup.old_heat_stacks('testcloud'), [])

    def test_failed_heat_stacks(self):
        """ Unit test for failed_heat_stacks function """
        self.assertEqual(ovb_tenant_cleanup.failed_heat_stacks('testcloud'),
                         ['baremetal_73703'])

    def test_progress_heat_stacks(self):
        """ Unit test for progress_heat_stacks function """
        self.assertEqual(ovb_tenant_cleanup.progress_heat_stacks('testcloud'),
                         (['39ce9687-0c9a-463f-b4c1-2d30f082f3cf'],
                          ['baremetal_123456']))


if __name__ == '__main__':
    unittest.main()
