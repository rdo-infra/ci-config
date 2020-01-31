import unittest

try:
    # Python3 imports
    from unittest.mock import Mock, patch
    import unittest.mock as mock
except ImportError:
    # Python2 imports
    from mock import Mock, patch
    import mock

from dlrn_hash import DlrnCommitDistroHash, DlrnAggregateHash, DlrnHashError, \
    DlrnHash
from test_unit_fixtures import sources


class TestDlrnHashSubClasses(unittest.TestCase):

    def test_build_valid(self):
        for hash_type, source_types in sources.items():
            values = source_types['dict']['valid']
            if hash_type == "commitdistro":
                dh = DlrnCommitDistroHash(commit_hash=values['commit_hash'],
                                          distro_hash=values['distro_hash'],
                                          timestamp=values['timestamp'])
                self.assertEqual(dh.commit_hash,
                                 source_types['dict']['valid']['commit_hash'])
                self.assertEqual(dh.distro_hash,
                                 source_types['dict']['valid']['distro_hash'])
            elif hash_type == "aggregate":
                aggregate_hash = source_types['dict']['valid'][
                    'aggregate_hash']
                dh = DlrnAggregateHash(aggregate_hash=values['aggregate_hash'],
                                       commit_hash=values['commit_hash'],
                                       distro_hash=values['distro_hash'],
                                       timestamp=values['timestamp'])
                self.assertEqual(dh.aggregate_hash, aggregate_hash)
        self.assertEqual(dh.timestamp,
                         source_types['dict']['valid']['timestamp'])

    def test_build_valid_from_source(self):
        for hash_type, source_types in sources.items():
            values = source_types['dict']['valid']
            if hash_type == "commitdistro":
                dh = DlrnCommitDistroHash(source=values)
                self.assertEqual(dh.commit_hash,
                                 source_types['dict']['valid']['commit_hash'])
                self.assertEqual(dh.distro_hash,
                                 source_types['dict']['valid']['distro_hash'])
            elif hash_type == "aggregate":
                aggregate_hash = source_types['dict']['valid'][
                    'aggregate_hash']
                dh = DlrnAggregateHash(source=values)
                self.assertEqual(dh.aggregate_hash, aggregate_hash)
        self.assertEqual(dh.timestamp,
                         source_types['dict']['valid']['timestamp'])

    def test_build_invalid_from_source(self):
        with self.assertRaises(DlrnHashError):
            source = sources['commitdistro']['dict']['invalid']
            DlrnCommitDistroHash(source=source)
        with self.assertRaises(DlrnHashError):
            source = sources['aggregate']['dict']['invalid']
            DlrnAggregateHash(source=source)


class TestDlrnHash(unittest.TestCase):

    def test_create_from_values(self):
        for hash_type, source_types in sources.items():
            dh = DlrnHash(**source_types['dict']['valid'])
            if hash_type == "commitdistro":
                self.assertEqual(type(dh), DlrnCommitDistroHash)
            elif hash_type == 'aggregate':
                self.assertEqual(type(dh), DlrnAggregateHash)

    def test_build_invalid(self):
        with self.assertRaises(DlrnHashError):
            DlrnHash(source=[])

    def test_create_from_dict(self):
        for hash_type, source_types in sources.items():
            dh = DlrnHash(source=source_types['dict']['valid'])
            if hash_type == "commitdistro":
                self.assertEqual(type(dh), DlrnCommitDistroHash)
            elif hash_type == "aggregate":
                self.assertEqual(type(dh), DlrnAggregateHash)
            with self.assertRaises(DlrnHashError):
                DlrnHash(source=source_types['dict']['invalid'])

    def test_create_from_object(self):
        # Prevent Mock class to identify as dict
        for hash_type, source_types in sources.items():
            source_valid = source_types['object']['valid']
            DlrnHash(source=source_valid)
            with self.assertRaises(DlrnHashError):
                source_invalid = source_types['object']['invalid']
                DlrnHash(source=source_invalid)

    def test_comparisons(self):
        non_dh = {}
        for hash_type, source_types in sources.items():
            dh1 = DlrnHash(source=source_types['object']['valid'])
            dh2 = DlrnHash(source=source_types['object']['valid'])
            self.assertEqual(dh1, dh2)
            dh2 = DlrnHash(source=source_types['object']['different'])
            self.assertNotEqual(dh1, dh2)
            with self.assertRaises(TypeError):
                (dh1 == non_dh)
            with self.assertRaises(TypeError):
                (dh1 != non_dh)
            dh1 = DlrnHash(source=source_types['object']['valid_notimestamp'])
            dh2 = DlrnHash(source=source_types['object']['valid_notimestamp'])
            self.assertEqual(dh1, dh2)

    def test_properties(self):
        for hash_type, source_types in sources.items():
            source = source_types['object']['valid']
            dh = DlrnHash(source=source)
            if hash_type == "commitdistro":
                full_hash = "{}_{}".format(source.commit_hash,
                                           source.distro_hash[:8])
                self.assertEqual(dh.full_hash, full_hash)
            elif hash_type == "aggregate":
                self.assertEqual(dh.full_hash, source.aggregate_hash)

    def test_dump_to_params(self):
        for hash_type, source_types in sources.items():
            params = Mock()
            dh = DlrnHash(source=source_types['object']['valid'])
            dh.dump_to_params(params)
            if hash_type == "commitdistro":
                self.assertEqual(params.commit_hash, dh.commit_hash)
                self.assertEqual(params.distro_hash, dh.distro_hash)
            elif hash_type == "aggregate":
                self.assertEqual(params.aggregate_hash, dh.aggregate_hash)
            self.assertEqual(params.timestamp, dh.timestamp)
