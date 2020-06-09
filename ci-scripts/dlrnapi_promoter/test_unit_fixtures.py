import os
import tempfile
import unittest

from config_legacy import PromoterLegacyConfig
from dlrnapi_promoter import arg_parser
from logic import Promoter

try:
    # Python3 imports
    from unittest.mock import Mock
except ImportError:
    # Python2 imports
    from mock import Mock


# Passwordles ssh key
SSH_CONTENT = """
-----BEGIN OPENSSH PRIVATE KEY-----
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
-----END OPENSSH PRIVATE KEY-----
"""

# Cases of ini configuration
# TODO: remove together with legacy config
test_ini_configurations = dict(
    not_ini='''
    I am not a ini file
    ''',
    missing_parameters='''
    [main]
    api_url: https://trunk.rdoproject.org/api-centos-master-uc
    username: ciuser
    dry_run: no
    log_file: /dev/nul
    latest_hashes_count: 10
    manifest_push: true

    [promote_from]
    current-tripleo: tripleo-ci-testing

    [current-tripleo]
    periodic-tripleo-centos-7-master-containers-build-push
    ''',
    missing_main='''
    [promote_from]
    current-tripleo: tripleo-ci-testing
    ''',
    missing_promotions_section='''
    [main]
    # missing mandatory parameters and sections
    distro_name: centos
    distro_version: 7
    release: master
    api_url: https://trunk.rdoproject.org/api-centos-master-uc
    username: ciuser
    dry_run: no
    log_file: /dev/null
    latest_hashes_count: 10
    manifest_push: true
    ''',
    missing_criteria_section='''
    [main]
    # missing mandatory parameters and sections
    distro_name: centos
    distro_version: 7
    release: master
    api_url: https://trunk.rdoproject.org/api-centos-master-uc
    username: ciuser
    dry_run: no
    log_file: /dev/null
    latest_hashes_count: 10
    manifest_push: true

    [promote_from]
    current-tripleo: tripleo-ci-testing
    ''',
    criteria_empty='''
    [main]
    distro_name: centos
    distro_version: 7
    release: master
    api_url: https://trunk.rdoproject.org/api-centos-master-uc
    username: ciuser
    dry_run: no
    log_file: /dev/null
    latest_hashes_count: 10
    manifest_push: true

    [promote_from]
    current-tripleo: tripleo-ci-testing

    [current-tripleo]
    ''',
    correct='''
    [main]
    distro_name: centos
    distro_version: 7
    release: master
    api_url: https://trunk.rdoproject.org/api-centos-master-uc
    username: ciuser
    dry_run: no
    log_file: /dev/null
    latest_hashes_count: 10
    manifest_push: true

    [promote_from]
    current-tripleo: tripleo-ci-testing

    [current-tripleo]
    periodic-tripleo-centos-7-master-containers-build-push
    periodic-tripleo-centos-7-master-standalone
    ''',
)


# These are preparation for all the types of dlrn_hashes we are going to test
# on the following test cases.
valid_commitdistro_kwargs = dict(commit_hash='abcd', distro_hash='defg',
                                 timestamp=1)
valid_commitdistro_notimestamp_kwargs = dict(commit_hash='a', distro_hash='b')
invalid_commitdistro_kwargs = dict(commit='a', distro='b')
different_commitdistro_kwargs = dict(commit_hash='b', distro_hash='c',
                                     timestamp=1)
different_commitdistro_notimestamp_kwargs = dict(commit_hash='a',
                                                 distro_hash='b')
valid_aggregate_kwargs = dict(aggregate_hash='abcd', commit_hash='defg',
                              distro_hash='hijk', timestamp=1)
valid_aggregate_notimestamp_kwargs = dict(aggregate_hash='a', commit_hash='b',
                                          distro_hash='c')
invalid_aggregate_kwargs = dict(aggregate='a')
different_aggregate_kwargs = dict(aggregate_hash='c', commit_hash='a',
                                  distro_hash='c', timestamp=1)
different_aggregate_notimestamp_kwargs = dict(aggregate_hash='a',
                                              commit_hash='b',
                                              distro_hash='c')

# Structured way to organize test cases by hash type and source type
# by commitdistro and aggregate hash types and by dict or object source tyep
hashes_test_cases = {
    'commitdistro': {
        "dict": {
            "valid": valid_commitdistro_kwargs,
            "valid_notimestamp":
                valid_commitdistro_notimestamp_kwargs,
            'invalid': invalid_commitdistro_kwargs,
            'different': different_commitdistro_kwargs,
            'different_notimestamp':
                different_commitdistro_notimestamp_kwargs
        },
        "object": {
            "valid": Mock(spec=type, **valid_commitdistro_kwargs),
            "valid_notimestamp":
                Mock(spec=type, **valid_commitdistro_notimestamp_kwargs),
            'invalid': Mock(spec=type, **invalid_commitdistro_kwargs),
            'different': Mock(spec=type, **different_commitdistro_kwargs),
            'different_notimestamp':
                Mock(spec=type, **different_commitdistro_notimestamp_kwargs)
        },
    },
    'aggregate': {
        "dict": {
            "valid": valid_aggregate_kwargs,
            "valid_notimestamp":
                valid_aggregate_notimestamp_kwargs,
            'invalid': invalid_aggregate_kwargs,
            'different': different_aggregate_kwargs,
            'different_notimestamp':
                different_aggregate_notimestamp_kwargs
        },
        "object": {
            "valid": Mock(spec=type, **valid_aggregate_kwargs),
            "valid_notimestamp":
                Mock(spec=type, **valid_aggregate_notimestamp_kwargs),
            'invalid': Mock(spec=type, **invalid_aggregate_kwargs),
            'different': Mock(spec=type, **different_aggregate_kwargs),
            'different_notimestamp':
                Mock(spec=type, **different_aggregate_notimestamp_kwargs),
        },
    },
}


# TODO: remove together with legacy config
class LegacyConfigSetup(unittest.TestCase):

    def setUp(self):
        content = test_ini_configurations['correct']
        fp, self.filepath = tempfile.mkstemp(prefix="instance_test")

        with os.fdopen(fp, "w") as test_file:
            test_file.write(content)

        cli = "--config-file {} promote-all".format(self.filepath)
        os.environ["DLRNAPI_PASSWORD"] = "test"
        overrides = {
            "default_qcow_server": "staging",
            "log_level": "DEBUG",
        }
        overrides_obj = type("FakeArgs", (), overrides)
        args = arg_parser(cmd_line=cli)
        config = PromoterLegacyConfig(args.config_file, overrides=overrides_obj)
        self.promoter = Promoter(config)

    def tearDown(self):
        os.unlink(self.filepath)
