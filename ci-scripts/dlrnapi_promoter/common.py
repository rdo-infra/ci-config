"""
This file contains general functions and classes
"""
import logging
import logging.handlers
import os
import sys


class PromotionError(Exception):
    pass


def str2bool(value):
    """
    Converts a string with a boolean value into a proper boolean
    mostly useful for variables coming from ini parser
    """
    if value in ['yes', 'true', 'True', 'on', '1']:
        return True
    return False


def setup_logging(name, log_level, log_file=None):
    """
    Sets up logging for the whole workflow, using the file provided in
    config
    If the process is start in a tty, we will log to console too
    :return: None
    """

    logger = logging.getLogger(name)
    # Since logging has a global configuration let's reset logger object
    # clear out any past configurations
    list(map(logger.removeHandler, logger.handlers[:]))
    list(map(logger.removeFilter, logger.filters[:]))

    logger.setLevel(log_level)
    log_formatter = logging.Formatter('%(asctime)s %(process)d '
                                      '%(levelname)-8s %(name)s '
                                      '%(message)s')
    if log_file is not None:
        log_handler = logging.handlers.WatchedFileHandler(
            os.path.expanduser(log_file))
        log_handler.setFormatter(log_formatter)
        logger.addHandler(log_handler)
    if sys.stdout.isatty():
        log_handler = logging.StreamHandler()
        log_handler.setFormatter(log_formatter)
        logger.addHandler(log_handler)
