import pytest
import mock
import tempest_file_downloader


@pytest.mark.parametrize("job_name", ['periodic-tripleo-ci-centos-7-ovb-1ctlr_2comp-featureset021-master'])
@pytest.mark.parametrize("log_file", ['stestr_results.html'])
@mock.patch('tempest_file_downloader.cache.add', autospec=True)
@mock.patch('tempest_file_downloader.tempfile.mkdtemp', autospec=True)
@mock.patch('tempest_file_downloader.download_tempest_file', autospec=True)
@mock.patch('requests.get')
def test_get_last_build_stestr(requests_mock, dump_dir_mock, tempest_cache_mock, job_name, log_file):
    dump_dir_mock.return_value = '/tmp/skiplist'
    build = tempest_file_downloader.get_last_build(job_name, log_file)
    assert (isinstance([build], list))
    tempest_cache_mock.assert_called_with('http://logs.rdoproject.org/75/24375/1/check/periodic-tripleo-ci-centos-7'
                                          '-ovb-1ctlr_2comp-featureset021-master/08cf5f8//logs/stestr_results.html',
                                          '/tmp/skiplist')
    dump_dir_mock.assert_called()
    assert (len(build) > 0)



@pytest.mark.parametrize("job_name", ['periodic-tripleo-ci-centos-7-ovb-1ctlr_2comp-featureset021-queens',
                                      'periodic-tripleo-ci-centos-7-ovb-1ctlr_2comp-featureset021-rocky',
                                      'periodic-tripleo-ci-centos-7-ovb-1ctlr_2comp-featureset021-stein'])
@pytest.mark.parametrize("log_file", ['tempest.html.gz'])
def ttest_get_last_build_tempest(job_name, log_file):
    build = tempest_file_downloader.get_last_build(job_name, log_file)
    assert (isinstance([build], list))
    assert (len(build) > 0)


@pytest.mark.parametrize("url", ['http://logs.rdoproject.org/openstack-periodic-master/opendev.org/openstack/tripleo'
                                 '-ci/master/periodic-tripleo-ci-centos-7-ovb-1ctlr_2comp-featureset021-master'
                                 '/5b535f9/logs/stestr_results.html',
                                 'http://logs.rdoproject.org/openstack-periodic-wednesday-weekend/opendev.org'
                                 '/openstack/tripleo-ci/master/periodic-tripleo-ci-centos-7-ovb-1ctlr_2comp'
                                 '-featureset021-queens/831a32d/logs/tempest.html.gz'])
@pytest.mark.parametrize("tempest_dump_dir", ['/tmp'])
def ttest_dowmload_tempest_file(url, tempest_dump_dir):
    result = tempest_file_downloader.download_tempest_file(url, tempest_dump_dir)
    assert (isinstance([result], list))
    assert (len(result) > 0)
