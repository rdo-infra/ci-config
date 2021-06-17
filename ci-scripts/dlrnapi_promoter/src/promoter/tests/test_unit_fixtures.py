import os
import shutil
import unittest

from promoter.config import PromoterConfigFactory
from promoter.logic import Promoter

try:
    # Python3 imports
    from unittest.mock import Mock
except ImportError:
    # Python2 imports
    from mock import Mock

# Passwordles ssh key
SSH_CONTENT = """-----BEGIN RSA PRIVATE KEY-----
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
-----END RSA PRIVATE KEY-----"""

# These are preparation for all the types of dlrn_hashes we are going to test
# on the following test cases.
valid_commitdistro_kwargs = dict(
    commit_hash='f6ef2e4e4e4cce030e5ef2f7799bff4e968af03a',
    distro_hash='41b4c09cabc2df6450eeb997594077fc7d4ebe6e',
    extended_hash='85ddd74e99da98ad07e637d0b42d4692910e4e70_'
                  '7ecd11cd44cbe7b93e4ff27d0049d937945d3a75',
    timestamp=1)
valid_commitdistro_notimestamp_kwargs = dict(
    commit_hash='ec60849c773e4649d22d4b976e7c5892596d4d1b',
    distro_hash='030bf177f0394ece3dc912dd22ae7ccee8e4af0b',
    extended_hash='35e7cd373aa33c4fe9dfc21ff41da81810c69715_'
                  '86d134f3ea6848af3f1968b8904ba0da1fa7a074')
valid_commitdistro_noextended_kwargs = dict(
    commit_hash='ec60849c773e4649d22d4b976e7c5892596d4d1b',
    distro_hash='030bf177f0394ece3dc912dd22ae7ccee8e4af0b',
    extended_hash='None')
invalid_commitdistro_kwargs = dict(
    commit='26c19986a58560b90bfa4b39bd3bc1ef43ad57f5',
    distro='34d2c7ae120f6c07767c5638f28d4a35515ade67',
    extended='e99c5941564f63e6c2f99592c0c6ff5ac815914a_'
             '6772f32196d090a6cd303471538fa963727a58e7')
different_commitdistro_kwargs = dict(
    commit_hash='4f4774d4e410ce72b024c185d3054cf649e5c578',
    distro_hash='fe88530aa04df13ebc63287c819c721740837aae',
    extended_hash='255baafa43d70533e93abb74a67f97b974ee314c_'
                  'eaf928319df5cdeb87e646e940eacc0402a49751',
    timestamp=1)
different_commitdistro_notimestamp_kwargs = dict(
    commit_hash='96e24bb1dbbac0313cea1f233f8cd918c6d820ac',
    distro_hash='c3a41aaf53b9ea10333387b7d40797ba2c1018d2',
    extended_hash='29c28719aaf8b6b58a75e9aa9d9307b6248e9717_'
                  '14078f4c7615d8b21a2a6d7c75afb84b4920f59b')
valid_aggregate_kwargs = dict(
    aggregate_hash='d7c3cd922f91d83aacb5d7555de9d5bc',
    commit_hash='f21ff147b907701bfbc840a1ee59a8014e77684a',
    distro_hash='ea06708141614decfdc4af687a26c9586a23b9ff',
    timestamp=1)
valid_aggregate_notimestamp_kwargs = dict(aggregate_hash='a', commit_hash='b',
                                          distro_hash='c')
invalid_aggregate_kwargs = dict(aggregate='a')
different_aggregate_kwargs = dict(aggregate_hash='c', commit_hash='a',
                                  distro_hash='c', timestamp=1)
different_aggregate_notimestamp_kwargs = dict(aggregate_hash='a',
                                              commit_hash='b',
                                              distro_hash='c')

log_dir = "~/web/promoter_logs/"

# Structured way to organize test cases by hash type and source type
# by commitdistro and aggregate hash types and by dict or object source tyep
hashes_test_cases = {
    'commitdistro': {
        "dict": {
            "valid": valid_commitdistro_kwargs,
            "valid_notimestamp":
                valid_commitdistro_notimestamp_kwargs,
            'valid_noextended': valid_commitdistro_noextended_kwargs,
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
            'valid_noextended': valid_aggregate_kwargs,
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
        log_d = os.path.expanduser(log_dir)
        if not os.path.exists(os.path.dirname(log_d)):
            os.makedirs(os.path.dirname(log_d))
        config_builder = PromoterConfigFactory()
        self.config = config_builder(
            os.path.join(
                config_builder.global_defaults['script_root'],
                config_builder.global_defaults['environment_config_root']),
            'CentOS-8/master.yaml')
        self.promoter = Promoter(self.config)

    def tearDown(self):
        try:
            log_d = os.path.expanduser(log_dir)
            shutil.rmtree(os.path.dirname(log_d))
        except Exception:
            pass
