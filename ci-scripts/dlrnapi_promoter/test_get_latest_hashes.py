from mock import patch, mock_open
import mock
import pytest
import urllib

# avoid pytest --collect-only errors with missing imports:
dlrnapi_promoter = pytest.importorskip('dlrnapi_promoter')


@mock.patch('dlrnapi_promoter.fetch_hashes')
def test_no_hashes_fetched_returns_empty_list(fetch_hashes_mock):

    old_hashes = []
    candidate_hashes = []
    fetch_hashes_mock.side_effect = [candidate_hashes, old_hashes]

    obtained_hashes = dlrnapi_promoter.get_latest_hashes(
        'dlrn_api', 'promote_name', 'curent_name', 3)

    fetch_hashes_mock.assert_has_calls([
        mock.call('dlrn_api', 'curent_name', count=3),
        mock.call('dlrn_api', 'promote_name', count=-1)])

    assert(len(obtained_hashes) == 0)


@mock.patch('dlrnapi_promoter.fetch_hashes')
def test_no_candidates_returns_empty_list(fetch_hashes_mock):

    old_hashes = [
        {
            'timestamp': '1528085424',
            'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884eda5',
            'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77eff5'
        }
    ]

    candidate_hashes = []
    fetch_hashes_mock.side_effect = [candidate_hashes, old_hashes]

    obtained_hashes = dlrnapi_promoter.get_latest_hashes(
        'dlrn_api', 'promote_name', 'curent_name', 3)

    fetch_hashes_mock.assert_has_calls([
        mock.call('dlrn_api', 'curent_name', count=3),
        mock.call('dlrn_api', 'promote_name', count=-1)])

    assert(len(obtained_hashes) == 0)


@mock.patch('dlrnapi_promoter.fetch_hashes')
def test_no_old_hashes_returns_candidates(fetch_hashes_mock):

    old_hashes = []

    candidate_hashes = [
        {
            'timestamp': '1528085424',
            'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884eda5',
            'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77eff5'
        },
        {
            'timestamp': '1528085434',
            'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884eda6',
            'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77eff6'
        }
    ]
    fetch_hashes_mock.side_effect = [candidate_hashes, old_hashes]

    obtained_hashes = dlrnapi_promoter.get_latest_hashes(
        'dlrn_api', 'promote_name', 'curent_name', 3)

    fetch_hashes_mock.assert_has_calls([
        mock.call('dlrn_api', 'curent_name', count=3),
        mock.call('dlrn_api', 'promote_name', count=-1)])

    assert(obtained_hashes == candidate_hashes)


@mock.patch('dlrnapi_promoter.fetch_hashes')
def test_old_hashes_get_filtered_from_candidates(fetch_hashes_mock):

    old_hashes = [
        {
            'timestamp': '1528085424',
            'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed24',
            'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef24'
        },
        {
            'timestamp': '1528085425',
            'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed25',
            'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef25'
        }
    ]

    candidate_hashes = [
        {
            'timestamp': '1528085427',
            'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed27',
            'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef27'
        },
        {
            'timestamp': '1528085423',
            'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed23',
            'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef23'
        },
        {
            'timestamp': '1528085425',
            'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed25',
            'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef25'
        },
        {
            'timestamp': '1528085424',
            'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed24',
            'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef24'
        },
        {
            'timestamp': '1528085426',
            'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed26',
            'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef26'
        },
    ]

    expected_hashes = [
        {
            'timestamp': '1528085427',
            'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed27',
            'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef27'
        },
        {
            'timestamp': '1528085426',
            'commit_hash': 'd1c5379369b24effdccfe5dde3e93bd21884ed26',
            'distro_hash': 'cd4fb616ac3065794b8a9156bbe70ede3d77ef26'
        },

    ]

    fetch_hashes_mock.side_effect = [candidate_hashes, old_hashes]

    obtained_hashes = dlrnapi_promoter.get_latest_hashes(
        'dlrn_api', 'promote_name', 'curent_name', 3)

    fetch_hashes_mock.assert_has_calls([
        mock.call('dlrn_api', 'curent_name', count=3),
        mock.call('dlrn_api', 'promote_name', count=-1)])

    assert(obtained_hashes == expected_hashes)


DLRN_TEST_DATA="[delorean]\nname=delorean-openstack-mistral-66d1776f1b992d3b5f593240f4a9bfa75e572f76\nbaseurl=https://trunk.rdoproject.org/centos7/66/d1/66d1776f1b992d3b5f593240f4a9bfa75e572f76_ae355860\nenabled=1\ngpgcheck=0\npriority=1\n"
def dummy_urlopen(url):
    return DLRN_TEST_DATA.splitlines()

#@mock.patch('dlrnapi_promoter.fetch_current_named_hashes')
@mock.patch.object(urllib, 'urlopen')
def test_fetch_current_named_hashes(mock_urllib):
    DLRN_TEST_DATA="[delorean]\nname=delorean-openstack-mistral-66d1776f1b992d3b5f593240f4a9bfa75e572f76\nbaseurl=https://trunk.rdoproject.org/centos7/66/d1/66d1776f1b992d3b5f593240f4a9bfa75e572f76_ae355860\nenabled=1\ngpgcheck=0\npriority=1\n"
    mock_urllib.return_value = dummy_urlopen("")
    #with patch("__builtin__.open", mock_open(read_data=DLRN_TEST_DATA)) as mock_file:
#    with mock.patch('__main__.open', mock_open(read_data=DLRN_TEST_DATA)) as m:
    thehashes = dlrnapi_promoter.fetch_current_named_hashes(("centos", "7"), "master", {"curent-tripleo": "foo", "current-tripleo-rdo": "bar"})
        #    fetch_named_hashes_mockashedsfdasfa

