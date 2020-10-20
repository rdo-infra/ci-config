import gerrit_changes
import test_data

def test_gerrit_changes():
    host = 'https://review.opendev.org'
    project = 'openstack/puppet-tripleo'
    pages = 1
    expected = test_data.data
    obtained = gerrit_changes.get_gerrit_data(host, project, pages)
    print(obtained)
    assert (expected == obtained)
