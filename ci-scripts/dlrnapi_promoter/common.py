"""
This file contains general functions and classes
"""
import logging
import logging.handlers
import os
import socket
import subprocess
import sys
import time

try:
    # In python 2 ConnectionRefusedError is not a builtin
    from socket import error as ConnectionRefusedError
except ImportError:
    pass

# FIXME(gcerami) Python27 doesn't have FilenotfoundError and PermissionError
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError
try:
    PermissionError
except NameError:
    PermissionError = IOError


class PromotionError(Exception):
    pass


class LockError(Exception):
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
        while connected and timeout > 0:
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


def get_root_paths(log=None):
    """
    Analyses the syspath and git root to understand where everithing is
    :param log: a log instance to write errors to
    :return: a tuple with the ci_config repo root, and the dir with the
    promoter python files
    """
    if log is None:
        log = logging.getLogger("get-root-paths")
    promoter_relpath = "ci-scripts/dlrnapi_promoter"
    promoter_root = os.path.abspath(sys.path[0])
    os.chdir(promoter_root)
    ci_config_root = promoter_root
    # Try to get a more precise value for git root if we can
    git_root_cmd = 'git rev-parse --show-toplevel'
    try:
        ci_config_root = subprocess.check_output(git_root_cmd.split())
    except subprocess.CalledProcessError:
        log.error("Unable to get git root dir, using %s", promoter_root)

    if not isinstance(ci_config_root, str):
        ci_config_root = ci_config_root.decode()
    ci_config_root = ci_config_root.strip()
    promoter_root = os.path.join(ci_config_root, promoter_relpath)

    return ci_config_root, promoter_root


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
        try:
            log_file = os.path.expanduser(log_file)
        except (FileNotFoundError, PermissionError):
            pass
        try:
            log_handler = logging.handlers.WatchedFileHandler(log_file)
        except (FileNotFoundError, PermissionError):
            logger.error("Invalid Log file: %s", log_file)
            raise LoggingError
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

        logger.info(log_setup_msg, logging.getLevelName(log_level))


def str_api_object(api_object):
    """
    converts the str of a dlrn api_object (that usually contain newlines)
    into a single line string
    :param api_object: The object to convert
    :return: A string with the conversion of the api_object.__str__ method
    """
    return str(api_object).replace('\n', ' ').replace('\r', ' ')


# Use atomic abstract socket creation as process lock
# no pid files to deal with
def get_lock(process_name):
    logger = logging.getLogger('promoter')
    # Without holding a reference to our socket somewhere it gets garbage
    # collected when the function exits
    get_lock._lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

    try:
        logger.debug('Trying to aquire promoter lock')
        get_lock._lock_socket.bind('\0' + process_name)
        logger.debug('Aquired promoter lock')
    except socket.error:
        logger.error('Another promoter process is running.')
        raise LockError
