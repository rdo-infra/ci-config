import unittest
from unittest import mock
import ovb_tenant_cleanup

class TestCleanupScript(unittest.TestCase):


    def test_remove_prefix(self):
        self.assertEqual(ovb_tenant_cleanup.remove_prefix("baremetal_763542_36_39000",
                                            "baremetal_"), "763542_36_39000")


    def test_remove_suffix(self):
        self.assertEqual(ovb_tenant_cleanup.remove_suffix("baremetal_763542_36_39000",
                                            ""), "baremetal_763542_36_39000")
        self.assertEqual(ovb_tenant_cleanup.remove_suffix("763542_36_39000-extra",
                                            "-extra"), "763542_36_39000")


    def test_fetch_identifier(self):
        self.assertEqual(ovb_tenant_cleanup.fetch_identifier("baremetal_763542_36_39000",
                                               "baremetal_", ""), "763542_36_39000")
        self.assertEqual(ovb_tenant_cleanup.fetch_identifier("baremetal_763542_36_39000-extra",
                                               "baremetal_", "-extra"), "763542_36_39000")


    def test_heat_stacks(self):
        with mock.patch('ovb_tenant_cleanup.heat_stacks',
                        return_value=['f20f49b2-0da1-41f1-a12b-be75eb1e4fff']):
            self.assertEqual(ovb_tenant_cleanup.heat_stacks(1, "baremetal_", False),
                             ['f20f49b2-0da1-41f1-a12b-be75eb1e4fff'])

        with mock.patch('ovb_tenant_cleanup.heat_stacks',
                        return_value=['f20f49b2-0da1-41f1-a12b-be75eb1e4fff',
                                      '51801d01-11e4-40cd-94a2-11e3ae538548',
                                      'ed440a48-cf87-4b8c-9650-05cf5d0308af',
                                      '2a5150da-9bc2-4ecd-b409-38f542620e15']):
            self.assertEqual(ovb_tenant_cleanup.heat_stacks(1, "baremetal_", True),
                             ['f20f49b2-0da1-41f1-a12b-be75eb1e4fff',
                              '51801d01-11e4-40cd-94a2-11e3ae538548',
                              'ed440a48-cf87-4b8c-9650-05cf5d0308af',
                              '2a5150da-9bc2-4ecd-b409-38f542620e15'])


if __name__ == "__main__":
    unittest.main()
