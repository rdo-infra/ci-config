"""
This file contains general functions and classes
"""


def str2bool(value):
    """
    Converts a string with a boolean value into a proper boolean
    """
    if value in ['yes', 'true', 'True', 'on', '1']:
        return True
    return False
