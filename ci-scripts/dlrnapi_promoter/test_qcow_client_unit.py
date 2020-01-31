import subprocess
try:
    # Python3 imports
    from unittest.mock import Mock, patch
    import unittest.mock as mock
except ImportError:
    # Python2 imports
    from mock import Mock, patch
    import mock

from common import PromotionError
from dlrn_hash import DlrnHash
from test_promoter_common_unit import ConfigSetup, sources


class TestQcowClient(ConfigSetup):

    def setUp(self):
        super(TestQcowClient, self).setUp()
        self.client = self.promoter.qcow_client

    @mock.patch('subprocess.check_output')
    def test_promote(self, check_output_mock):
        candidate_hash = DlrnHash(source=sources['aggregate']['dict']['valid'])
        target_label = "test"

        check_output_mock.return_value = b"test log"
        self.client.promote(candidate_hash, target_label)

        assert subprocess.check_output.called
        exception = subprocess.CalledProcessError(1, 2)
        exception.output = b"test"
        check_output_mock.side_effect = exception
        with self.assertRaises(PromotionError):
            self.client.promote(candidate_hash, target_label)