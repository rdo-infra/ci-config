#!/usr/bin/env python
"""
Main file for the promoter
"""
import argparse
import logging
import os
from datetime import date, datetime

import common
from common import LockError, get_log_file
from config import PromoterConfigFactory
from dlrn_hash import DlrnHash, DlrnHashError
from logic import Promoter

DEFAULT_CONFIG_RELEASE = "CentOS-8/master.yaml"
DEFAULT_CONFIG_ROOT = "staging"  # "rdo" for production environment


def add_logs(log_file, archival_file):
    banner1 = "\n\n" + "#" * 10 + datetime.now().isoformat(
        timespec='minutes') + "#" * 10 + "\n\n"
    log_data = open(log_file).read()
    filemode = 'a'
    if not os.path.isfile(archival_file):
        filemode = 'w'

    with open(archival_file, filemode) as f:
        f.write(banner1)
        f.write(log_data)


def promote_all(promoter, args):
    promoter.promote_all()


def force_promote(promoter, args):
    try:
        candidate_hash = DlrnHash(source=args)
    except DlrnHashError:
        print("Unable to generate a valid candidate hash from the information"
              " provided")
        raise

    promoter.promote(candidate_hash, args.candidate_label, args.target_label)


def arg_parser(cmd_line=None, config=None):
    """
    Parse the command line or the parameter to pass to the rest of the workflow
    :param cmd_line: A string containing a command line (mainly used for
    testing)
    :return: An args object with overrides for the configuration
    """
    default_formatter = argparse.ArgumentDefaultsHelpFormatter
    main_parser = argparse.ArgumentParser(description="Promoter workflow",
                                          formatter_class=default_formatter)
    main_parser.add_argument("--release-config", required=False,
                             default=DEFAULT_CONFIG_RELEASE,
                             help="Release config file")
    main_parser.add_argument("--config-root", required=False,
                             default=DEFAULT_CONFIG_ROOT,
                             help="Specify the environment type "
                                  "Default: staging, For production"
                                  "use rdo and downstream")
    main_parser.add_argument("--log-level",
                             default='INFO',
                             help="Set the log level")
    command_parser = main_parser.add_subparsers(dest='subcommand')
    command_parser.required = True
    promote_all_parser = command_parser.add_parser('promote-all',
                                                   help="Promote everything")
    # promote-all has no sub-arguments
    promote_all_parser.set_defaults(handler=promote_all)

    force_promote_parser = \
        command_parser.add_parser('force-promote',
                                  help="Force promotion of a specific hash, "
                                       "bypassing candidate selection",
                                  formatter_class=default_formatter)
    # force-promote arguments
    force_promote_parser.add_argument("--commit-hash", required=True,
                                      help="The commit hash part for the "
                                           "candidate hash")
    force_promote_parser.add_argument("--distro-hash", required=True,
                                      help="The distro hash part for the "
                                           "candidate hash")
    force_promote_parser.add_argument("--aggregate-hash",
                                      help="The aggregate hash part for the "
                                           "candidate hash")
    force_promote_parser.add_argument("--allowed-clients",
                                      default="registries_client,qcow_client,"
                                              "dlrn_client",
                                      help="The comma separated list of "
                                           "clients allowed to perfom the "
                                           "promotion")
    force_promote_parser.add_argument("candidate_label",
                                      help="The label associated with the "
                                           "candidate hash")
    force_promote_parser.add_argument("target_label",
                                      help="The label to promoted "
                                           "the candidate hash to")
    force_promote_parser.set_defaults(handler=force_promote)

    if cmd_line is not None:
        args = main_parser.parse_args(cmd_line.split())
    else:
        args = main_parser.parse_args()
    return args


def main(cmd_line=None):
    """
    This main will gather the cli arguments and start the promoter
    :param cmd_line: (optional) we can pass a string simulating a command
    line string with arguments. Useful for testing the main function
    :return: None
    """
    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger('dlrnapi_promoter')
    log.setLevel(logging.DEBUG)

    args = arg_parser(cmd_line=cmd_line)
    try:
        common.get_lock("promoter")
    except LockError:
        print(
            "Another promoter instance is running, wait for it to finish or "
            "kill it and then retry")
        raise
    if hasattr(args, "release_config"):
        CONFIG_RELEASE = args.release_config
    else:
        CONFIG_RELEASE = DEFAULT_CONFIG_RELEASE

    log.info("Checking for log directory")
    log_file = os.path.expanduser(get_log_file(args.config_root,
                                               CONFIG_RELEASE))
    log_dir = "/".join(log_file.split("/")[:-1])
    if not os.path.exists(log_dir):
        log.info("Creating log directory : {}".format(log_dir))
        os.makedirs(log_dir)

    config_builder = PromoterConfigFactory(**{'log_file': log_file})
    config = config_builder(args.config_root,
                            CONFIG_RELEASE,
                            cli_args=args)
    promoter = Promoter(config)

    args.handler(promoter, args)
    date_today = date.today().isoformat()
    log_file_name = log_file.split(".")[0] + "_" + date_today + ".log"
    add_logs(log_file, log_file_name)
    log.info("Logs appended to: {}".format(log_file_name))


if __name__ == '__main__':
    main()
