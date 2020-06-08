#!/usr/bin/env python
"""
Main file for the promoter
"""
import argparse
import os

import common
from common import LockError
from config import PromoterConfigFactory
from dlrn_hash import DlrnHash, DlrnHashError
from logic import Promoter


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
    main_parser.add_argument("--config-file", required=False,
                             help="The config file")
    main_parser.add_argument("--log-level",
                             default='debug',  # TODO akahat fix this
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
                                      default=None,  # TODO akahat change it
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

    args = arg_parser(cmd_line=cmd_line)
    try:
        common.get_lock("promoter")
    except LockError:
        print(
            "Another promoter instance is running, wait for it to finish or "
            "kill it and then retry")
        raise

    config_builder = PromoterConfigFactory()
    config = config_builder(
        os.path.join(config_builder.global_defaults['script_root'],
                     config_builder.global_defaults['environment_config_root']),
        'CentOS-8/master.yaml')
    promoter = Promoter(config)

    args.handler(promoter, args)


if __name__ == '__main__':
    main()
