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
import dlrnapi_client
import logging
import logging.handlers
import os
import sys

from common import str2bool
from config import PromoterConfig
from logic import PromoterLogic
# Import previous content from the legacy_promoter file
import legacy_promoter
from legacy_promoter import legacy_main
from legacy_promoter import fetch_current_named_hashes


class Promoter(object):
    """
    This class will drive the hig level process
    """

    log = logging.getLogger('promoter')

    def __init__(self, args):
        self.config = PromoterConfig(args.config_file)
        self.setup_logging()
        self.logic = PromoterLogic(self.config)

    def setup_logging(self):
        """
        Sets up logging for the whole workflow, using the file provided in
        config
        If the process is start in a tty, we will log to console too
        :return: None
        """
        self.log.setLevel(logging.DEBUG)
        log_handler = logging.handlers.WatchedFileHandler(
            os.path.expanduser(self.config.log_file))
        log_formatter = logging.Formatter('%(asctime)s %(process)d '
                                          '%(levelname)-8s %(name)s '
                                          '%(message)s')
        log_handler.setFormatter(log_formatter)
        self.log.addHandler(log_handler)
        if sys.stdout.isatty():
            log_handler = logging.StreamHandler()
            log_handler.setFormatter(log_formatter)
            self.log.addHandler(log_handler)

    def start_process(self):
        """
        High level process starter
        :return: None
        """
        self.log.warning("This workflow is using the new modularized code")
        try:
            self.logic.promote_all_links()
        except Exception as e:
            self.log.exception(e)
        self.log.info("FINISHED promotion process")


# Wrappers for the old code
def main(cmd_line=None):
    """
    This main will select which execution path to take, between legacy and new
    code
    """
    main_parser = argparse.ArgumentParser(description="Promoter workflow")
    main_parser.add_argument("config_file", help="The config file")
    main_parser.add_argument("--force-legacy", action="store_true",
                             help="Force the use of the legacy code")

    if cmd_line is not None:
        args = main_parser.parse_args(cmd_line.split())
    else:
        args = main_parser.parse_args()
    logger = logging.getLogger('promoter')
    # Main execution paths branch we either use legacy code or we use
    # modularized
    if args.force_legacy or str2bool(os.environ.get("PROMOTER_FORCE_LEGACY",
                                                    False)):
        # Legacy code supports only a single argument
        sys.argv = [sys.argv[0], args.config_file]
        # legacy_main is imported from legacy code
        logger.warning("This workflow is using legacy promotion code")
        legacy_main()
    else:
        promoter = Promoter(args)
        promoter.start_process()


if __name__ == '__main__':
    main()
