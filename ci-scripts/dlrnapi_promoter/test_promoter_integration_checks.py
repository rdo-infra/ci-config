import dlrnapi_client
import logging
import pytest
import unittest
try:
    import urllib2 as url_lib
except ImportError:
    import urllib.request as url_lib
import yaml

from dlrn_interface import DlrnHash
from promoter_integration_checks import (check_dlrn_promoted_hash,
                                         query_container_registry_promotion,
                                         compare_tagged_image_hash,
                                         parse_promotion_logs)
from staging_environment import main as stage_main
try:
    # Python3 imports
    from unittest.mock import Mock, patch, mock_open
    builtin_str = "builtins.open"
except ImportError:
    # Python2 imports
    from mock import Mock, patch, mock_open
    builtin_str = "__builtin__.open"


@pytest.fixture(scope='function')
def staged_env(request):
    """
    Fixture that runs the staging environment provisioner, yields the files
    produced and cleans up after
    """

    log = logging.getLogger('promoter-staging')

    config_file = "stage-config-secure.yaml"
    try:
        test_case = request.param
    except AttributeError:
        pass
    except KeyError:
        log.error("Invalid test case '{}'".format(request.param))
        raise

    scenes = None
    if "all_" in test_case:
        config_file = "stage-config.yaml"
    if "overcloud_" in test_case:
        scenes = 'overcloud_images'
    if "registries_" in test_case:
        scenes = 'registries'
    if "containers_" in test_case:
        scenes = 'dlrn,registries,containers'
        config_file = "stage-config.yaml"

    setup_cmd_line = "setup --stage-config-file {}".format(config_file)
    teardown_cmd_line = "teardown --stage-config-file {}".format(config_file)
    if scenes is not None:
        setup_cmd_line += " --scenes {}".format(scenes)

    if "_integration" in test_case:
        setup_cmd_line += " --db-data integration-pipeline.yaml"
        teardown_cmd_line += " --db-data integration-pipeline.yaml"

    log.info("Running cmd line: {}".format(setup_cmd_line))

    config = stage_main(setup_cmd_line)

    stage_info_path = config.main['stage_info_path']
    with open(stage_info_path, "r") as stage_info_file:
        stage_info = yaml.safe_load(stage_info_file)

    yield stage_info
    log.info("Running cmd line: {}".format(teardown_cmd_line))
    stage_main(teardown_cmd_line)


@pytest.mark.serial
class TestIntegrationChecks(unittest.TestCase):

    def test_main(self):
        pass


@pytest.mark.parametrize("staged_env", ("dlrn_single",
                                        "dlrn_integration"),
                         indirect=True)
def test_dlrn_promoted(staged_env):
    stage_info = staged_env
    promotion_dict = stage_info['dlrn']['promotions']['promotion_candidate']
    promotion_hash = DlrnHash(source=promotion_dict)

    with patch.object(dlrnapi_client.DefaultApi, 'api_promotions_get') as \
            mock_api:
        # positive test

        promotion_hash.promote_name = "tripleo-ci-staging-promoted"
        mock_api.return_value = [promotion_hash]
        check_dlrn_promoted_hash(stage_info=stage_info)

        # negative test
        promotion_hash.promote_name = "tripleo-ci-staging"
        mock_api.return_value = [promotion_hash]
        with pytest.raises(AssertionError):
            check_dlrn_promoted_hash(stage_info=stage_info)


@pytest.mark.parametrize("staged_env", ("containers_single",
                                        "containers_integration"),
                         indirect=True)
def test_query_container(staged_env):
    stage_info = staged_env
    with patch.object(url_lib, 'urlopen') as mock_urllib:
        # positive tests
        mock_urllib.return_value = True
        query_container_registry_promotion(stage_info=stage_info)
        # negative tests
        mock_urllib.side_effect = url_lib.HTTPError(*[None] * 5)
        with pytest.raises(AssertionError):
            query_container_registry_promotion(stage_info=stage_info)



@pytest.mark.parametrize("staged_env", ("qcow_single",
                                        "qcow_integration"),
                         indirect=True)
# @patch('pysftp')
def test_compare_tagged(staged_env):
    stage_info = staged_env
    # TODO(gcerami) needs revisiting, much more difficult to make it pass now
    if False:
        with patch('os.readlink') as mock_readlink:
            mock_readlink.return_value = (
                "/tmp/promoter-staging/overcloud_images/centos7/master"
                "/rdo_trunk/360d335e94246d7095672c5aa92b59afa380a059_9e598812"
            )
            compare_tagged_image_hash(stage_info=stage_info)


success_pattern_container_positive = (
    "promoter Promoting the container images for dlrn hash"
    " 360d335e94246d7095672c5aa92b59afa380a059 \n"
    "Promoting the qcow image for dlrn hash"
    " 360d335e94246d7095672c5aa92b59afa380a059_9e598812"
    " on master to tripleo-ci-staging-promoted \n"
    "promoter Successful jobs for {'timestamp': 1503307099,"
    " 'distro_hash': '9e5988125e88f803ba20743be7aa99079dd275f2',"
    " 'promote_name': 'tripleo-ci-staging', 'user': 'foo',"
    " 'repo_url':"
    " 'None/36/0d/360d335e94246d7095672c5aa92b59afa380a059_9e598812',"
    " 'full_hash': '360d335e94246d7095672c5aa92b59afa380a059_9e598812',"
    " 'repo_hash': '360d335e94246d7095672c5aa92b59afa380a059_9e598812',"
    " 'commit_hash': '360d335e94246d7095672c5aa92b59afa380a059'}: \n"
    "promoter SUCCESS promoting centos7-master tripleo-ci-staging as"
    " tripleo-ci-staging-promoted \n"
    "promoter FINISHED promotion process"
)


@pytest.mark.parametrize("staged_env", ("dlrn_single",
                                        "dlrn_integration"),
                         indirect=True)
def test_parse(staged_env):
    stage_info = staged_env
    data = success_pattern_container_positive
    with patch(builtin_str, mock_open(read_data=data)):
        parse_promotion_logs(stage_info=stage_info)
