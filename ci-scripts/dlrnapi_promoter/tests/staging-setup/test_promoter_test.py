import dlrnapi_client
import os
import pytest
import unittest
try:
    from unittest.mock import Mock, patch, mock_open
except ImportError:
    from mock import Mock, patch, mock_open
try:
    import urllib2 as url_lib
except ImportError:
    import urllib.request as url_lib
import yaml

from promoter_test import (check_dlrn_promoted_hash,
                           query_container_registry_promotion,
                           compare_tagged_image_hash,
                           parse_promotion_logs)

from staging_environment import StagedEnvironment, load_config


@pytest.mark.serial
class TestIntegrationTests(unittest.TestCase):

    def setUp(self):
        overrides = {
            'components': "all",
            'stage-info-path': "/tmp/stage-info.yaml",
            'dry-run': True,
            'promoter_user': "centos",
        }
        self.config = load_config(overrides, db_filepath="/tmp/sqlite-test.db")
        self.staged_env = StagedEnvironment(self.config)
        self.staged_env.setup()

        with open(self.config['stage-info-path'], "r") as stage_info_path:
            self.stage_info = yaml.safe_load(stage_info_path)

        self.success_pattern_container_positive = (
            "promoter Promoting the container images for dlrn hash"
            " 1c67b1ab8c6fe273d4e175a14f0df5d3cbbd0edc"
        )

        self.success_patter_container_negative = (
            "promoter Promoting the container images for dlrn hash"
            " aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )

    def Teardown(self):
        self.staged_env.teardown()

    @patch.object(dlrnapi_client.DefaultApi, 'api_promotions_get')
    def test_dlrn_promoted(self, mock_api):
        # positive test
        promotion = Mock()
        promotion.promote_name = "tripleo-ci-staging-promoted"
        mock_api.return_value = [promotion]
        check_dlrn_promoted_hash(self.stage_info)

        # negative test
        promotion = Mock()
        promotion.promote_name = "tripleo-ci-staging"
        mock_api.return_value = [promotion]
        with self.assertRaises(AssertionError):
            check_dlrn_promoted_hash(self.stage_info)

    @patch.object(url_lib, 'urlopen')
    def test_query_container(self, mock_urllib):
        # positive tests
        mock_urllib.return_value = True
        query_container_registry_promotion(self.stage_info)
        # negative tests
        mock_urllib.side_effect = url_lib.HTTPError(*[None] * 5)
        with self.assertRaises(AssertionError):
            query_container_registry_promotion(self.stage_info)

    @patch('os.readlink')
    # @patch('pysftp')
    def test_compare_tagged(self, mock_readlink):
        mock_readlink.return_value = \
            "1c67b1ab8c6fe273d4e175a14f0df5d3cbbd0edc_8170b868"
        compare_tagged_image_hash(self.stage_info)


#    def test_parse(self):
#        data = self.success_pattern_container_positive
#        with patch("builtins.open", mock_open(read_data=data)) as mock_file:
#            parse_promotion_logs(self.stage_info)
#
#        data = self.success_pattern_container_negative
#        with patch("builtins.open", mock_open(read_data=data)) as mock_file:
#            parse_promotion_logs(self.stage_info)
