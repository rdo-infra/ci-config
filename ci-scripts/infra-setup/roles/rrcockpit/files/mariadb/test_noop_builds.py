import pytest
import noop_build

# We get all the combinations and attack gerrit
@pytest.mark.parametrize("release", ['master', 'rocky', 'queens', 'pike'])
@pytest.mark.parametrize("type", ["upstream", "rdo"])
def test_infra(release, type):
    messages = noop_build.get_messages(release)
    assert(isinstance(messages, list))
    assert(len(messages) > 0)
    last_message = noop_build.get_last_message(messages, type)
    assert(last_message)
    builds = noop_build.get_builds(last_message)
    assert(builds)
    assert(isinstance(builds, list))
    assert(len(builds) > 0)
    csv = noop_build.compose_as_csv(builds)
    assert(csv)
    assert(len(csv) > 0)

