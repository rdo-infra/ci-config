"""
This file contains general functions and classes
"""

# Global variable needed for the hash check
# We should try to remove it when we get to make the hash check function
# modularized
# start_named_hashes - named hashes at promotion start
# can check they are not changed before we push containers/images/links.
# {'current-tripleo': 'xyz', 'previous-current-tripleo': 'abc' ... }
# https://tree.taiga.io/project/tripleo-ci-board/task/1325
start_named_hashes = {}


def str2bool(value):
    """
    Converts a string with a boolean value into a proper boolean
    """
    if value in ['yes', 'true', 'True', 'on', '1']:
        return True
    return False
