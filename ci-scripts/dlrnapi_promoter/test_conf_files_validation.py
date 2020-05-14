import os
import logging

from common import get_root_paths, setup_logging
from config import PromoterConfig


def test_conf_files():
    """
    Check that conf files for configuring the promoter can be loaded as
    correct configuration
    :return:
    """
    setup_logging("test_conf_file", logging.ERROR)
    log = logging.getLogger("test_conf_file")
    __, promoter_root = get_root_paths("test_conf_file")
    errors = False
    for root, __, files in os.walk(os.path.join(promoter_root, "config")):
        for file_name in files:
            if '.yaml' in file_name:
                full_path = os.path.join(root, file_name)
                if 'component' in full_path:
                    continue
                try:
                    PromoterConfig(full_path, checks=['criteria'])
                except Exception as config_except:
                    log.exception(config_except)
                    errors = True

    if errors:
        raise Exception("Some config files contain errors")
