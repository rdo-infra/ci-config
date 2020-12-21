""" Unit test for ovb_tenant_cleanup.py """
import unittest
from unittest import mock
import json
import ovb_tenant_cleanup

class TestCleanupScript(unittest.TestCase):


    def test_remove_prefix(self):
        """ Unit test for remove_prefix function """
        self.assertEqual(ovb_tenant_cleanup.remove_prefix("baremetal_763542_36_39000",
                                            "baremetal_"), "763542_36_39000")


    def test_remove_suffix(self):
        """ Unit test for remove_suffix function """
        self.assertEqual(ovb_tenant_cleanup.remove_suffix("baremetal_763542_36_39000",
                                            ""), "baremetal_763542_36_39000")
        self.assertEqual(ovb_tenant_cleanup.remove_suffix("763542_36_39000-extra",
                                            "-extra"), "763542_36_39000")


    def test_fetch_identifier(self):
        """ Unit test for fetch_identifier function """
        self.assertEqual(ovb_tenant_cleanup.fetch_identifier("baremetal_763542_36_39000",
                                               "baremetal_", ""), "763542_36_39000")
        self.assertEqual(ovb_tenant_cleanup.fetch_identifier("baremetal_763542_36_39000-extra",
                                               "baremetal_", "-extra"), "763542_36_39000")


    def test_fetch_resources(self):
        """ Unit test for fetch_resources function """
        with self.assertRaises(ValueError):
            ovb_tenant_cleanup.fetch_resources('')


    def test_heat_stacks(self):
        """ Unit test for heat_stacks function """
        with open('test_stack.json') as file:
            loaded_data = json.load(file)
        json_data_string = json.dumps(loaded_data)
        with mock.patch('ovb_tenant_cleanup.fetch_resources',
                        return_value=json_data_string):
            obtained = ovb_tenant_cleanup.heat_stacks(300, "baremetal_", True)
            expected = ['6abab7fc-8069-4c90-b7b2-3392e1a5a5e6',
                        '3a432a14-52bf-4f3a-8df2-163a308c86b5',
                        '97c6a22a-70c8-4fb6-9922-ade66092e785',
                        '51801d01-11e4-40cd-94a2-11e3ae538548',
                        'ed440a48-cf87-4b8c-9650-05cf5d0308af',
                        '2a5150da-9bc2-4ecd-b409-38f542620e15']
            self.assertCountEqual(obtained,expected)
            obtained = ovb_tenant_cleanup.heat_stacks(300, "baremetal_", False)
            expected = ['3a432a14-52bf-4f3a-8df2-163a308c86b5',
                        '97c6a22a-70c8-4fb6-9922-ade66092e785',
                        '6abab7fc-8069-4c90-b7b2-3392e1a5a5e6']
            self.assertCountEqual(obtained,expected)

    def test_servers_with_identifier(self):
        """ Unit test for servers_with_identifier function """
        with open('test_server.json') as file:
            loaded_data = json.load(file)
        json_data_string = json.dumps(loaded_data)
        with mock.patch('ovb_tenant_cleanup.fetch_resources',
                        return_value=json_data_string):
            obtained = ovb_tenant_cleanup.servers_with_identifier("765249_2_63940")
            expected = ['33dd2e35-3441-4fda-abce-60aae5fb1309',
                        'f8e55112-11f8-4da5-9512-45df467fefcc']
            self.assertCountEqual(obtained,expected)
            obtained = ovb_tenant_cleanup.servers_with_identifier("123456")
            expected = []
            self.assertCountEqual(obtained,expected)


    def test_failed_heat_stacks(self):
        """ Unit test for failed_heat_stacks function """
        with open('test_stack.json') as file:
            loaded_data = json.load(file)
        json_data_string = json.dumps(loaded_data)
        with mock.patch('ovb_tenant_cleanup.fetch_resources',
                        return_value=json_data_string):
            obtained = ovb_tenant_cleanup.failed_heat_stacks()
            expected = ['baremetal_765249_2_63940_2',
                        'baremetal_765249_2_63940_1']
            self.assertCountEqual(obtained,expected)


    def test_networks_with_identifier(self):
        """ Unit test for networks_with_identifier function """
        with open('test_network.json') as file:
            loaded_data = json.load(file)
        json_data_string = json.dumps(loaded_data)
        with mock.patch('ovb_tenant_cleanup.fetch_resources',
                        return_value=json_data_string):
            obtained = ovb_tenant_cleanup.networks_with_identifier("765249_2_63940")
            expected = ['45dfd47c-e8b1-4a82-814b-4deaa70c9cc2',
                        'dac7eb56-a36a-4479-a4c1-a267b1caf9d1']
            self.assertCountEqual(obtained,expected)
            obtained = ovb_tenant_cleanup.networks_with_identifier("123456")
            expected = []
            self.assertCountEqual(obtained,expected)

    def test_subnets_with_identifier(self):
        """ Unit test for subnets_with_identifier function """
        with open('test_subnet.json') as file:
            loaded_data = json.load(file)
        json_data_string = json.dumps(loaded_data)
        with mock.patch('ovb_tenant_cleanup.fetch_resources',
                        return_value=json_data_string):
            obtained = ovb_tenant_cleanup.subnets_with_identifier("765249_2_63940")
            expected = ['11437903-cdd8-4037-93d9-bbd345557ff1',
                        '76886820-581f-4932-a247-1258b2b3981c']
            self.assertCountEqual(obtained,expected)
            obtained = ovb_tenant_cleanup.subnets_with_identifier("123456")
            expected = []
            self.assertCountEqual(obtained,expected)


    def test_ports_of_subnets(self):
        """ Unit test for ports_of_subnets function """
        with open('test_port.json') as file:
            loaded_data = json.load(file)
        json_data_string = json.dumps(loaded_data)
        with mock.patch('ovb_tenant_cleanup.fetch_resources',
                        return_value=json_data_string):
            obtained = ovb_tenant_cleanup.ports_of_subnets(
                       ['11437903-cdd8-4037-93d9-bbd345557ff1',
                        '76886820-581f-4932-a247-1258b2b3981c'])
            expected = ['bbf75ec8-1d38-47b7-b811-ab7c4c0ddf0a',
                        'e2604f23-d132-42ae-b288-073ab57d2c99']
            self.assertCountEqual(obtained,expected)
            obtained = ovb_tenant_cleanup.ports_of_subnets([])
            expected = []
            self.assertCountEqual(obtained,expected)


if __name__ == "__main__":
    unittest.main()
