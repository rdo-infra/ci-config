"""
This file contains classes and function to build a configuration object that
can be passed to all the new and legacy functions in the workflow.
"""

import configparser
import logging


class ConfigError(Exception):
    pass


class PromoterConfig(object):
    """
    This class builds a singleton object to be passed to all the other
    functions in the workflow. It's backwards compatible with the legacy code
    as it constructs a legacy object to pass to them
    """

    log = logging.getLogger("promoter")

    def __init__(self, config_path):
        """
        Initialize the config object loading from ini file and builds also
        the legacy object and parameters.
        :param config_path: the path to the configuration file to load
        """
        try:
            cparser = configparser.ConfigParser(allow_no_value=True)
            cparser.read(config_path)

            # Legacy method, will be used to pass to functions that have not yep
            # been migrated
            self.legacy_config = cparser
        except configparser.MissingSectionHeaderError:
            self.log.error("Unable to load config file {}".format(config_path))
            raise ConfigError
