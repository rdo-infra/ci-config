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

from config import PromoterConfig
from common import str2bool
# Import previous content from the legacy_promoter file
from legacy_promoter import legacy_main
from legacy_promoter import setup_logging
from logic import PromoterLogic


def promoter(args):
    config = PromoterConfig(args.config_file)
    # setup_logging is imported from legacy code
    setup_logging(config.legacy_config.get('main', 'log_file'))
    logger = logging.getLogger('promoter')
    logger.warning("This workflow is using the new modularized code")
    try:
        logic = PromoterLogic(config)
        logic.promote_all_links()
    except Exception as e:
        logger.exception(e)
    logger.info("FINISHED promotion_process")


# Wrappers for the old code
def main():
    main_parser = argparse.ArgumentParser(description="Promoter workflow")
    main_parser.add_argument("config_file", help="The config file")
    main_parser.add_argument("--force-legacy", action="store_true",
                             help="Force the use of the legacy code")
    args = main_parser.parse_args()
    # Main execution paths branch we either use legacy code or we use
    # modularized
    if args.force_legacy or str2bool(os.environ.get("PROMOTER_FORCE_LEGACY",
                                                    False)):
        # Legacy code supports only a single argument
        sys.argv = [sys.argv[0], args.config_file]
        # legacy_main is imported from legacy code
        legacy_main()
    else:
        promoter(args)


if __name__ == '__main__':
    main()
