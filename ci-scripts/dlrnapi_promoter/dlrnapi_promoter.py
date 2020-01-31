#!/usr/bin/env python
"""
Main file for the promoter
"""
import argparse

from config import PromoterConfigBase
from logic import Promoter


def arg_parser(cmd_line=None):
    """
    Parse the command line or the parameter to pass to the rest of the workflow
    :param cmd_line: A string containing a command line (mainly used for
    testing)
    :return: An args object with overrides for the configuration
    """
    main_parser = argparse.ArgumentParser(description="Promoter workflow")
    main_parser.add_argument("config_file", help="The config file")
    main_parser.add_argument("--log-level",
                             default=PromoterConfigBase.defaults['log_level'],
                             help="Set the log level")

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
    promoter = Promoter(args.config_file, overrides=args)
    promoter.promote_all()


if __name__ == '__main__':
    main()
