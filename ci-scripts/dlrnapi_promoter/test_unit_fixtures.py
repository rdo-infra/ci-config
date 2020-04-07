import os
import tempfile
import unittest

from dlrnapi_promoter import arg_parser
from logic import Promoter

try:
    # Python3 imports
    from unittest.mock import Mock
    import unittest.mock as mock
except ImportError:
    # Python2 imports
    from mock import Mock
    import mock

# Cases of ini configuration
test_ini_configurations = dict(
    empty_yaml="",
    not_yaml='''
    I am not a yaml file
    ''',
    invalid_yaml='''
    [main]
    invalid: 1
    ''',
    missing_promotions_section='''
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
    missing_criteria='''
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

    promotions:
      current-tripleo: {}
    ''',
    empty_criteria='''
    distro_name: centos
    distro_version: 7
    release: master
    api_url: https://trunk.rdoproject.org/api-centos-master-uc
    username: ciuser
    dry_run: no
    log_file: /dev/null
    latest_hashes_count: 10
    manifest_push: true

    promotions:
      current-tripleo:
        criteria: {}
    ''',
    correct='''
    distro_name: centos
    distro_version: 7
    release: master
    api_url: https://trunk.rdoproject.org/api-centos-master-uc
    username: ciuser
    dry_run: no
    log_file: /dev/null
    latest_hashes_count: 10
    manifest_push: true

    promotions:
      current-tripleo:
        candidate_label: tripleo-ci-testing
        criteria:
          - periodic-tripleo-centos-7-master-containers-build-push
          - periodic-tripleo-centos-7-master-standalone
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


class ConfigSetup(unittest.TestCase):

    def setUp(self):
        content = test_ini_configurations['correct']
        fp, self.filepath = tempfile.mkstemp(prefix="instance_test")
        with os.fdopen(fp, "w") as test_file:
            test_file.write(content)
        cli = "--config-file {} promote-all".format(self.filepath)
        args = arg_parser(cmd_line=cli)
        os.environ["DLRNAPI_PASSWORD"] = "test"
        self.promoter = Promoter(config_file=args.config_file)

    def tearDown(self):
        os.unlink(self.filepath)
