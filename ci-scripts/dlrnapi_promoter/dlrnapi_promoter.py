#!/usr/bin/env python
"""
Main file for the promoter
"""
import argparse

from common import LockError, get_lock
from config import PromoterConfigBase
from logic import Promoter
from dlrn_hash import DlrnHash, DlrnHashError, DlrnAggregateHash


def promote_all(args):
    promoter = Promoter(args.config_file, overrides=args)
    promoter.promote_all()


def force_promote(args):
    promoter = Promoter(args.config_file, overrides=args)

    try:
        candidate_hash = DlrnHash(source=args)
    except DlrnHashError:
        print("Unable to generate a valid candidate hash from the information"
              " provided")
        raise

    promoter.promote(candidate_hash, args.candidate_label, args.target_label)


def arg_parser(cmd_line=None):
    """
    Parse the command line or the parameter to pass to the rest of the workflow
    :param cmd_line: A string containing a command line (mainly used for
    testing)
    :return: An args object with overrides for the configuration
    """
    main_parser = argparse.ArgumentParser(description="Promoter workflow")
    main_parser.add_argument("--config-file", required=True,
                             help="The config file")
    main_parser.add_argument("--log-level",
                             default=PromoterConfigBase.defaults['log_level'],
                             help="Set the log level")
    command_parser = main_parser.add_subparsers()
    promote_all_parser = command_parser.add_parser('promote-all',
                                                   help="Promote everything")
    # promote-all has no subarguments
    promote_all_parser.set_defaults(handler=promote_all)

    force_promote_parser = \
        command_parser.add_parser('force-promote',
                                  help="Force promotion of a specific hash, "
                                       "bypassing candidate selection")
    # force-promote arguments
    force_promote_parser.add_argument("--commit-hash")
    force_promote_parser.add_argument("--distro-hash")
    force_promote_parser.add_argument("--aggregate-hash")
    allowed_clients_default = PromoterConfigBase.defaults['allowed_clients']
    force_promote_parser.add_argument("--allowed-clients",
                                      default=allowed_clients_default)
    force_promote_parser.add_argument("candidate_label")
    force_promote_parser.add_argument("target_label")
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
    try:
        get_lock("promoter")
    except LockError:
        print(
            "Another promoter instance is running, wait for it to finish or "
            "kill it and then retry")
    args = arg_parser(cmd_line=cmd_line)
    args.handler(args)


if __name__ == '__main__':
    main()
