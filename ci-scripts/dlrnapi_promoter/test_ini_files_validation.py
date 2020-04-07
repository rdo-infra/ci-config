import os
import logging

from common import get_root_paths, setup_logging
from config import PromoterConfigFactory


def test_ini_files():
    """
    Check that ini files for configuring the promoter can be loaded as
    correct configuration
    :return:
    """
    setup_logging("test_ini_file", logging.ERROR)
    log = logging.getLogger("test_ini_file")
    __, promoter_root = get_root_paths("test_ini_file")
    errors = False
    for root, __, files in os.walk(os.path.join(promoter_root, "config")):
        for file in files:
            if '.ini' in file:
                full_path = os.path.join(root, file)
                try:
                    PromoterConfigFactory(full_path, checks=['criteria'])
                except Exception as config_except:
                    log.exception(config_except)
                    errors = True

    if errors:
        raise Exception("Some config files contain errors")
