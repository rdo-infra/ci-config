"""
This file contains classes and function to build a configuration object that
can be passed to all the new and legacy functions in the workflow.
"""

try:
    # Python 3 import
    import configparser as ini_parser
except ImportError:
    # Python 2 import
    import ConfigParser as ini_parser

import logging
import os
import subprocess
import sys

from common import str2bool


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
        # Get git repo root on which to base all relative paths
        relpath = "ci-scripts/dlrnapi_promoter"
        script_root = os.path.abspath(sys.path[0]).replace(relpath, "")
        os.chdir(script_root)
        # Try to get a more precise value for git root if we can
        git_root_cmd = 'git rev-parse --show-toplevel'
        try:
            root = subprocess.check_output(git_root_cmd.split())
            self.git_root = root.decode().strip()
        except subprocess.CalledProcessError:
            self.log.error("Unable to get git root dir, using {}"
                           "".format(script_root))
            self.git_root = script_root
        try:
            cparser = ini_parser.ConfigParser(allow_no_value=True)
            cparser.read(config_path)
            self.data = dict(cparser.items())
            self.load_from_ini()

            # Legacy method, will be used to pass to functions that have not yet
            # been migrated
            self.legacy_config = cparser
        except ini_parser.MissingSectionHeaderError:
            self.log.error("Unable to load config file %s", config_path)
            raise ConfigError
        except ConfigError:
            self.log.error("Error in configuration file %s", config_path)
            raise

    def load_from_ini(self):
        """
        Loads configuration from a INI file. There are several exceptions
        that can block the load
        - Missing main section
        - Missing criteria section for one of the specified candidates
        - Missing jobs in criteria section
        - Missing mandatory parameters
        - Missing password
        """

        conf_ok = True
        # Main parameters
        try:
            data_main = self.data['main']
        except KeyError:
            self.log.error("Missing main section")
            raise ConfigError

        # Mandatory
        mandatory_parameters = [
            "distro_name",
            "distro_version",
            "release",
            "api_url",
            "log_file",
            "username"
        ]
        for param in mandatory_parameters:
            try:
                setattr(self, param, data_main[param])
            except KeyError:
                conf_ok = False
                self.log.error("Missing mandatory parameter: %s", param)

        # Mangling and derivatives
        if hasattr(self, "distro_name"):
            self.distro_name = self.distro_name.lower()
        if hasattr(self, "distro_name") and hasattr(self, "distro_version"):
            self.distro = "{}{}".format(self.distro_name, self.distro_version)
        if hasattr(self, "username"):
            self.dlrnauth_username = self.username
            delattr(self, "username")

        # DLRN authentication
        try:
            self.dlrnauth_password = os.environ["DLRNAPI_PASSWORD"]
        except KeyError:
            self.log.error("Missing dlrnapi password")
            conf_ok = False

        # Promotion maps
        try:
            self.promotion_steps_map = self.data['promote_from']
        except KeyError:
            self.promotion_steps_map = []
            self.log.error("Missing promotion_from section")
            conf_ok = False
        self.promotion_criteria_map = {}
        for target_name, candidate_name in self.promotion_steps_map.items():
            try:
                criteria = set(list(self.data[target_name]))
                self.promotion_criteria_map[target_name] = criteria
                # replaces promote_all_links - label reject condition
                if not criteria:
                    self.log.error("No jobs in criteria for target %s",
                                   target_name)
                    conf_ok = False
            except KeyError:
                self.log.error("Missing criteria section for target %s",
                               target_name)
                conf_ok = False

        # Optional parameters
        self.dry_run = str2bool(self.get_path("main/dry_run", "false"))
        self.manifest_push = str2bool(self.get_path("main/manifest_push",
                                                    "false"))
        self.target_registries_push = str2bool(self.get_path(
            "main/target_registries_push", "true"))
        self.latest_hashes_count = int(self.get_path(
            "main/latest_hashes_count", 10))
        self.pipeline_type = self.get_path("main/target_registries_push",
                                           "single")

        # Allow promotion for the endpoints. For example, a release like
        # ocata may specify to no allow containers promotion
        self.allowed_clients = \
            self.get_path("main/allowed_clients",
                          "dlrn_client,qcow_client,registries_client").split(
                ',')

        if not conf_ok:
            raise ConfigError

    def get_multikeys(self, search_data, keys):
        """
        recursive function to retrieve a value from a nested dictionary whose
        path is specified in keys
        E.g  get_multikeys(dict, ['main', 'subsection', 'key1']) is the same as
        dict['main']['subsection']['key1']
        :param search_data: the dictionary to explore
        :param keys:  the keys list representing the path
        :return: the value of the leaf dictionary at the end of the path
        """
        if not keys:
            return search_data
        else:
            return self.get_multikeys(search_data[keys[0]], keys[1:])

    def get_path(self, key_string, *args):
        """
        translated a string like "main/subsection/key1" in a list of keys as
        a path to pass to the get_multikeys method, and the calls the method.
        :param key_string: the string containing the keys path
        :param args: if specified args[0] is used as default value when a ke
        does not exist
        :return: the value if the key_string exists or the default if specified.
        """
        keys = key_string.split("/")
        try:
            value = self.get_multikeys(self.data, keys)
        except KeyError:
            if args[0]:
                return args[0]
            else:
                raise

        return value
