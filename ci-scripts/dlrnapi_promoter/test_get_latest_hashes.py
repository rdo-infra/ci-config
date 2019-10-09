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


def test_named_hashes_unchanged():

    promote_from = {"current-tripleo": "foo", "current-tripleo-rdo": "bar"}
    start_named_hashes = dlrnapi_promoter.fetch_current_named_hashes(
        ("centos", "7"), "master", promote_from)
    named_hashes_now = dlrnapi_promoter.fetch_current_named_hashes(
        ("centos", "7"), "master", promote_from)

    # assert hashes are retrieved correctly by fetch_current_named_hashes
    assert(start_named_hashes.keys() == promote_from.keys())

    # assert they are equal - this might fail if run during promotion
    assert(start_named_hashes == named_hashes_now)

    # positive test for hashes_unchanged
    dlrnapi_promoter.start_named_hashes = start_named_hashes
    dlrnapi_promoter.check_named_hashes_unchanged(("centos", "7"), "master",
                                                  promote_from)

    # negative test
    dlrnapi_promoter.start_named_hashes = {"foo": "bar"}
    with pytest.raises(Exception):
        dlrnapi_promoter.check_named_hashes_unchanged(
            ("centos", "7"), "master", promote_from)
