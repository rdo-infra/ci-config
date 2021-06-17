import unittest

try:
    # Python3 imports
    from unittest.mock import Mock
except ImportError:
    # Python2 imports
    from mock import Mock

from promoter.dlrn_hash import (DlrnAggregateHash,
                                DlrnCommitDistroExtendedHash, DlrnHash,
                                DlrnHashError)

from .test_unit_fixtures import hashes_test_cases


def get_commit_dir(hash_dict, hash_type="commitdistro"):
    if isinstance(hash_dict, dict):
        commit_hash = hash_dict.get("commit_hash")
        distro_hash = hash_dict.get("distro_hash")
    else:
        commit_hash = hash_dict.commit_hash
        distro_hash = hash_dict.distro_hash
    if hash_type == 'commitdistro':
        try:
            extended_hash = hash_dict.extended_hash
        except (AttributeError):
            extended_hash = hash_dict.get('extended_hash')
        e_hash = '_'
        if extended_hash:
            e_d_hash, e_c_hash = extended_hash.split("_")
            e_hash += "{}_{}".format(e_d_hash[:8], e_c_hash[:8])

            return "{}/{}/{}_{}{}".format(commit_hash[:2], commit_hash[2:4],
                                          commit_hash, distro_hash[:8], e_hash)
    elif hash_type == "aggregate":
        try:
            aggregate_hash = hash_dict.aggregate_hash
        except (AttributeError):
            aggregate_hash = hash_dict.get("aggregate_hash")

        return "{}/{}/{}".format(aggregate_hash[:2], aggregate_hash[2:4],
                                 aggregate_hash)


class TestDlrnHashSubClasses(unittest.TestCase):

    def test_build_valid(self):
        for hash_type, source_types in hashes_test_cases.items():
            values = source_types['dict']['valid']
            if hash_type == "commitdistro":
                dh = DlrnCommitDistroExtendedHash(
                    commit_hash=values['commit_hash'],
                    distro_hash=values['distro_hash'],
                    extended_hash=values['extended_hash'],
                    timestamp=values['timestamp'])
                self.assertEqual(dh.commit_hash,
                                 source_types['dict']['valid']['commit_hash'])
                self.assertEqual(dh.distro_hash,
                                 source_types['dict']['valid']['distro_hash'])
                self.assertEqual(dh.extended_hash,
                                 source_types['dict']['valid']['extended_hash'])
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
        for hash_type, source_types in hashes_test_cases.items():
            values = source_types['dict']['valid']
            if hash_type == "commitdistro":
                dh = DlrnCommitDistroExtendedHash(source=values)
                self.assertEqual(dh.commit_hash,
                                 source_types['dict']['valid']['commit_hash'])
                self.assertEqual(dh.distro_hash,
                                 source_types['dict']['valid']['distro_hash'])
                self.assertEqual(dh.extended_hash,
                                 source_types['dict']['valid']['extended_hash'])
            elif hash_type == "aggregate":
                aggregate_hash = source_types['dict']['valid'][
                    'aggregate_hash']
                dh = DlrnAggregateHash(source=values)
                self.assertEqual(dh.aggregate_hash, aggregate_hash)
                self.assertEqual(dh.extended_hash, None)
        self.assertEqual(dh.timestamp,
                         source_types['dict']['valid']['timestamp'])

    def test_build_invalid_from_source(self):
        with self.assertRaises(DlrnHashError):
            source = hashes_test_cases['commitdistro']['dict']['invalid']
            DlrnCommitDistroExtendedHash(source=source)
        with self.assertRaises(DlrnHashError):
            source = hashes_test_cases['aggregate']['dict']['invalid']
            DlrnAggregateHash(source=source)

    def test_build_valid_extended_from_source(self):
        for hash_type, source_types in hashes_test_cases.items():
            values = source_types['dict']['valid_noextended']
            if hash_type == 'commitdistro':
                dh = DlrnCommitDistroExtendedHash(source=values)
                self.assertEqual(dh.commit_hash,
                                 source_types['dict']['valid_noextended'][
                                     'commit_hash'])
                self.assertEqual(dh.distro_hash,
                                 source_types['dict']['valid_noextended'][
                                     'distro_hash'])
                self.assertEqual(dh.extended_hash, None)
            elif hash_type == "aggregate":
                aggregate_hash = source_types['dict']['valid'][
                    'aggregate_hash']
                dh = DlrnAggregateHash(source=values)
                self.assertEqual(dh.aggregate_hash, aggregate_hash)
                self.assertEqual(dh.extended_hash, None)


class TestDlrnHash(unittest.TestCase):

    def test_create_from_values(self):
        for hash_type, source_types in hashes_test_cases.items():
            dh = DlrnHash(**source_types['dict']['valid'])
            if hash_type == "commitdistro":
                self.assertEqual(type(dh), DlrnCommitDistroExtendedHash)
            elif hash_type == 'aggregate':
                self.assertEqual(type(dh), DlrnAggregateHash)

    def test_build_invalid(self):
        with self.assertRaises(DlrnHashError):
            DlrnHash(source=[])

    def test_create_from_dict(self):
        for hash_type, source_types in hashes_test_cases.items():
            dh = DlrnHash(source=source_types['dict']['valid'])
            if hash_type == "commitdistro":
                self.assertEqual(type(dh), DlrnCommitDistroExtendedHash)
            elif hash_type == "aggregate":
                self.assertEqual(type(dh), DlrnAggregateHash)
            with self.assertRaises(DlrnHashError):
                DlrnHash(source=source_types['dict']['invalid'])

    def test_create_from_object(self):
        # Prevent Mock class to identify as dict
        for hash_type, source_types in hashes_test_cases.items():
            source_valid = source_types['object']['valid']
            DlrnHash(source=source_valid)
            with self.assertRaises(DlrnHashError):
                source_invalid = source_types['object']['invalid']
                DlrnHash(source=source_invalid)

    def test_comparisons(self):
        non_dh = {}
        for hash_type, source_types in hashes_test_cases.items():
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
        for hash_type, source_types in hashes_test_cases.items():
            source = source_types['object']['valid']
            dh = DlrnHash(source=source)
            if hash_type == "commitdistro":
                e_d_hash, e_c_hash = source.extended_hash.split("_")
                full_hash = "{}_{}_{}_{}".format(source.commit_hash,
                                                 source.distro_hash[:8],
                                                 e_d_hash[:8], e_c_hash[:8])
                self.assertEqual(dh.full_hash, full_hash)
            elif hash_type == "aggregate":
                self.assertEqual(dh.full_hash, source.aggregate_hash)

    def test_dump_to_params(self):
        for hash_type, source_types in hashes_test_cases.items():
            params = Mock()
            dh = DlrnHash(source=source_types['object']['valid'])
            dh.dump_to_params(params)
            if hash_type == "commitdistro":
                self.assertEqual(params.commit_hash, dh.commit_hash)
                self.assertEqual(params.distro_hash, dh.distro_hash)
            elif hash_type == "aggregate":
                self.assertEqual(params.aggregate_hash, dh.aggregate_hash)
            self.assertEqual(params.timestamp, dh.timestamp)

    def test_commit_dir(self):
        for hash_type, source_types in hashes_test_cases.items():
            dh = DlrnHash(source=source_types['object']['valid'])
            if hash_type == "commitdistro":
                commit_dir = get_commit_dir(source_types['object'][
                                                'valid'])
                self.assertEqual(dh.commit_dir, commit_dir)
            elif hash_type == "aggregate":
                dh.label = "label"
                commit_dir = get_commit_dir(source_types['object']['valid'],
                                            "aggregate")
                self.assertEqual(dh.commit_dir, "label/{}".format(commit_dir))

    def test_commit_dir_no_label(self):
        for hash_type, source_types in hashes_test_cases.items():
            dh = DlrnHash(source=source_types['object']['valid'])
            if hash_type == "commitdistro":
                commit_dir = get_commit_dir(source_types['object']['valid'])
                self.assertEqual(dh.commit_dir, commit_dir)
            elif hash_type == "aggregate":
                commit_dir = get_commit_dir(source_types['object']['valid'],
                                            'aggregate')
                self.assertEqual(dh.commit_dir, commit_dir)

    def test_commit_dir_component(self):
        for hash_type, source_types in hashes_test_cases.items():
            dh = DlrnHash(source=source_types['object']['valid'])
            if hash_type == "commitdistro":
                dh.component = "component1"
                commit_dir = get_commit_dir(source_types['object']['valid'])
                self.assertEqual(dh.commit_dir,
                                 "component/component1/{}".format(commit_dir))
