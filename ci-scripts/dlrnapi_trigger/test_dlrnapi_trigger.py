import mock

from dlrnapi_trigger import check_trigger_condition
from dlrnapi_client.models import Promotion, CIVote

api_promotions_get = [
    Promotion(
        commit_hash='49998bd3356842923fef5029443ecae6b2555535',
        distro_hash='2970104410bf047570f50b218d828c73f95f27d3',
        promote_name='tripleo-ci-testing',
        repo_hash='49998bd3356842923fef5029443ecae6b2555535_29701044',
        repo_url=('https = //trunk.rdoproject.org/centos7/'
                  '49/99/49998bd3356842923fef5029443ecae6b2555535_29701044'),
        timestamp=1551417073,
        user='review_rdoproject_org'),
    Promotion(
        commit_hash='49998bd3356842923fef5029443ecae6b2555535',
        distro_hash='2970104410bf047570f50b218d828c73f95f27d3',
        promote_name='tripleo-ci-testing',
        repo_hash='49998bd3356842923fef5029443ecae6b2555535_29701044',
        repo_url=('https = //trunk.rdoproject.org/centos7/'
                  '49/99/49998bd3356842923fef5029443ecae6b2555535_29701044'),
        timestamp=1551391879,
        user='review_rdoproject_org'),
    Promotion(
        commit_hash='e33841879c959b60f97bf22d936741961b7a0bcf',
        distro_hash='94dc48e51e21d255e92c1e1c8202b985ad3b1589',
        promote_name='tripleo-ci-testing',
        repo_hash='e33841879c959b60f97bf22d936741961b7a0bcf_94dc48e5',
        repo_url=('https = //trunk.rdoproject.org/centos7/'
                  'e3/38/e33841879c959b60f97bf22d936741961b7a0bcf_94dc48e5'),
        timestamp=1551345174,
        user='review_rdoproject_org')
]

api_repo_status_get = [
    CIVote(
        commit_hash='49998bd3356842923fef5029443ecae6b2555535',
        distro_hash='2970104410bf047570f50b218d828c73f95f27d3',
        in_progress=False,
        job_id=('periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset030'
                '-master'),
        notes='',
        success=True,
        timestamp=1551428403,
        url=(
            'https://logs.rdoproject.org/openstack-periodic/git.openstack.org/'
            'openstack-infra/tripleo-ci/master/'
            'periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset030-master/'
            '8ed900e')),
    CIVote(
        commit_hash='49998bd3356842923fef5029443ecae6b2555535',
        distro_hash='2970104410bf047570f50b218d828c73f95f27d3',
        in_progress=False,
        job_id='periodic-ovb-3ctlr_1comp_1supp-featureset039',
        notes='',
        success=False,
        timestamp=1551428534,
        url=(
            'https://logs.rdoproject.org/openstack-periodic/git.openstack.org/'
            'openstack-infra/tripleo-ci/master/'
            'periodic-tripleo-ci-centos-7-ovb-3ctlr_1comp_1supp-'
            'featureset039-master/2791714')),
    CIVote(
        commit_hash='49998bd3356842923fef5029443ecae6b2555535',
        distro_hash='2970104410bf047570f50b218d828c73f95f27d3',
        in_progress=False,
        job_id=('periodic-tripleo-ci-centos-7-ovb-3ctlr_1comp_1supp-'
                'featureset039-master'),
        notes='',
        success=False,
        timestamp=1551428540,
        url=(
            'https://logs.rdoproject.org/openstack-periodic/git.openstack.org/'
            'openstack-infra/tripleo-ci/master/'
            'periodic-tripleo-ci-centos-7-ovb-3ctlr_1comp_1supp-'
            'featureset039-master/2791714'))
]

launch_job_success = CIVote(
    commit_hash='49998bd3356842923fef5029443ecae6b2555535',
    distro_hash='2970104410bf047570f50b218d828c73f95f27d3',
    in_progress=False,
    job_id='periodic-baremetal-featureset666',
    notes='',
    success=True,
    timestamp=1551437024,
    url='https://logs.rdoproject.org/27/164127/11/check/hello-dlrn/4291a4b')

wait_job_success = CIVote(
    commit_hash='49998bd3356842923fef5029443ecae6b2555535',
    distro_hash='2970104410bf047570f50b218d828c73f95f27d3',
    in_progress=False,
    job_id='periodic-tripleo-centos-7-master-containers-build',
    notes='',
    success=True,
    timestamp=1551437024,
    url='https://logs.rdoproject.org/27/164127/11/check/hello-dlrn/4291a4b')

wait_job_failure = CIVote(
    commit_hash='49998bd3356842923fef5029443ecae6b2555535',
    distro_hash='2970104410bf047570f50b218d828c73f95f27d3',
    in_progress=False,
    job_id='periodic-tripleo-centos-7-master-containers-build',
    notes='',
    success=False,
    timestamp=1551437024,
    url='https://logs.rdoproject.org/27/164127/11/check/hello-dlrn/4291a4b')


@mock.patch('dlrnapi_client.apis.default_api.DefaultApi')
def test_trigger_on_wait_job_sucess_and_no_launch_job(dlrn_mock):
    dlrn_mock.api_promotions_get.return_value = api_promotions_get
    dlrn_mock.api_repo_status_get.return_value = api_repo_status_get + [
        wait_job_success
    ]
    promotion_name = 'tripleo-ci-testing'
    wait_job_name = 'periodic-tripleo-centos-7-master-containers-build'
    launch_job_name = 'periodic-baremetal-featureset666'
    assert (check_trigger_condition(dlrn_mock, promotion_name, wait_job_name,
                                    launch_job_name))


@mock.patch('dlrnapi_client.apis.default_api.DefaultApi')
def test_trigger_on_first_wait_job_sucess_and_no_launch_job(dlrn_mock):
    dlrn_mock.api_promotions_get.return_value = api_promotions_get
    dlrn_mock.api_repo_status_get.return_value = api_repo_status_get + [
        wait_job_success, wait_job_failure
    ]
    promotion_name = 'tripleo-ci-testing'
    wait_job_name = 'periodic-tripleo-centos-7-master-containers-build'
    launch_job_name = 'periodic-baremetal-featureset666'
    assert (check_trigger_condition(dlrn_mock, promotion_name, wait_job_name,
                                    launch_job_name))


@mock.patch('dlrnapi_client.apis.default_api.DefaultApi')
def test_dont_trigger_on_wait_job_failure(dlrn_mock):
    dlrn_mock.api_promotions_get.return_value = api_promotions_get
    dlrn_mock.api_repo_status_get.return_value = api_repo_status_get + [
        wait_job_failure
    ]
    promotion_name = 'tripleo-ci-testing'
    wait_job_name = 'periodic-tripleo-centos-7-master-containers-build'
    launch_job_name = 'periodic-baremetal-featureset666'
    assert (not check_trigger_condition(dlrn_mock, promotion_name,
                                        wait_job_name, launch_job_name))


@mock.patch('dlrnapi_client.apis.default_api.DefaultApi')
def test_dont_trigger_on_first_wait_job_failure(dlrn_mock):
    dlrn_mock.api_promotions_get.return_value = api_promotions_get
    dlrn_mock.api_repo_status_get.return_value = api_repo_status_get + [
        wait_job_failure, wait_job_success
    ]
    promotion_name = 'tripleo-ci-testing'
    wait_job_name = 'periodic-tripleo-centos-7-master-containers-build'
    launch_job_name = 'periodic-baremetal-featureset666'
    assert (not check_trigger_condition(dlrn_mock, promotion_name,
                                        wait_job_name, launch_job_name))


@mock.patch('dlrnapi_client.apis.default_api.DefaultApi')
def test_dont_trigger_on_launch_job_already_run(dlrn_mock):
    dlrn_mock.api_promotions_get.return_value = api_promotions_get
    dlrn_mock.api_repo_status_get.return_value = api_repo_status_get + [
        launch_job_success
    ]
    promotion_name = 'tripleo-ci-testing'
    wait_job_name = 'periodic-tripleo-centos-7-master-containers-build'
    launch_job_name = 'periodic-baremetal-featureset666'
    assert (not check_trigger_condition(dlrn_mock, promotion_name,
                                        wait_job_name, launch_job_name))
