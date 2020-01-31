"""
This file contains general functions and classes
"""
import logging
import logging.handlers
import os
import socket
import sys
import time

try:
    # In python 2 ConnectionRefusedError is not a builtin
    from socket import error as ConnectionRefusedError
except ImportError:
    pass


class PromotionError(Exception):
    pass


class LoggingError(Exception):
    pass


def str2bool(value):
    """
    Converts a string with a boolean value into a proper boolean
    mostly useful for variables coming from ini parser
    """
    if value in ['yes', 'true', 'True', 'on', '1']:
        return True
    return False


def check_port(host, port, timeout=None, port_mode="open"):
    """
    Check for connection to a host:port within a timeout
    :param host: A string with the host
    :param port: A integer with the port
    :param timeout:  An integer with the timeout, if None an unresobnably
    high value is set
    :param port_mode: decide to check if the port is open or closed
    :return: A bool to verify if the connection was successful
    """
    timeout = timeout
    if timeout is None:
        timeout = 999999
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if port_mode == "open":
        connected = False

        while timeout > 0 and not connected:
            try:
                sock.connect((host, port))
                connected = True
            except ConnectionRefusedError:
                # retry in 1 sec
                time.sleep(1)
                timeout -= 1
        if not connected:
            return False
        return True

    elif port_mode == "closed":
        connected = True
        while connected and timeout < timeout:
            try:
                sock.connect((host, port))
                # retry in 1 sec
                time.sleep(1)
                timeout -= 1
            except ConnectionRefusedError:
                connected = False
        if connected:
            return False
        return True


def close_logging(name):
    """
    Since logging has a global configuration let's reset logger object
    clear out any past configurations
    :return:
    """
    logger = logging.getLogger(name)
    print("Deconfiguring Logger with name: %s" % name)
    list(map(logger.removeHandler, logger.handlers[:]))
    list(map(logger.removeFilter, logger.filters[:]))


def setup_logging(name, log_level, log_file=None):
    """
    Sets up logging for the whole workflow, using the file provided in
    config
    If the process is start in a tty, we will log to console too
    :return: None
    """

    close_logging(name)
    log_setup_msg = "Set up logging level %s on: "
    log_handlers = []

    logger = logging.getLogger(name)

    logger.setLevel(log_level)
    log_formatter = logging.Formatter('%(asctime)s %(process)d '
                                      '%(levelname)-8s %(name)s '
                                      '%(message)s')
    if log_file is not None:
        log_handler = logging.handlers.WatchedFileHandler(
            os.path.expanduser(log_file))
        log_handler.setFormatter(log_formatter)
        logger.addHandler(log_handler)
        log_handlers.append(" file {}".format(log_file))
    if sys.stdout.isatty():
        log_handler = logging.StreamHandler()
        log_handler.setFormatter(log_formatter)
        logger.addHandler(log_handler)
        log_handlers.append("console")

    if log_handlers:
        log_setup_msg += " ,".join(log_handlers)
    else:
        print("Could not setup logging")

    logger.info(log_setup_msg, logging.getLevelName(log_level))
