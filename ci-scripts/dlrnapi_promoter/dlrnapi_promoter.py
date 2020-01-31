#!/usr/bin/env python
"""
This file is currently in transition mode.
Almost all previous content has been transferred to the legacy_promoter
file, and the function called in the main are imported from there.
This serves as basis for the transition of the code to a more modularized
codebase To prepare for the implementation of component pipeline
"""
from __future__ import print_function

import argparse
import logging
import os
import sys

from common import str2bool
from config import PromoterConfigBase
from logic import Promoter
# Import previous content from the legacy_promoter file
from legacy_promoter import legacy_main


def arg_parser(cmd_line=None):
    main_parser = argparse.ArgumentParser(description="Promoter workflow")
    main_parser.add_argument("config_file", help="The config file")
    main_parser.add_argument("--force-legacy", action="store_true",
                             help="Force the use of the legacy code")
    main_parser.add_argument("--log-level",
                             default=PromoterConfigBase.defaults['log_level'],
                             help="Force the use of the legacy code")

    if cmd_line is not None:
        args = main_parser.parse_args(cmd_line.split())
    else:
        args = main_parser.parse_args()

    return args


def main(cmd_line=None):
    """
    This main will gather the cli arguments and select which execution path to
    take, between legacy and new code
    :param cmd_line: (optional) we can pass a string simulating a command
    line string with arguments. Useful for testing the main function
    :return: None
    """

    args = arg_parser(cmd_line=cmd_line)
    # Main execution paths branch we either use legacy code or we use
    # modularized
    if args.force_legacy or str2bool(os.environ.get("PROMOTER_FORCE_LEGACY",
                                                    False)):
        # Legacy code supports only a single argument
        sys.argv = [sys.argv[0], args.config_file]
        # legacy_main is imported from legacy code
        legacy_main()
    else:
        promoter = Promoter(config_file=args.config_file, ovverides=args)
        promoter.promote_all()


if __name__ == '__main__':
    main()
