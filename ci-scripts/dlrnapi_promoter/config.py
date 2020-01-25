"""
This file contains classes and function to build a configuration object that
can be passed to all the new and legacy functions in the workflow.
"""

import configparser
import dlrnapi_client
import logging


from legacy_promoter import fetch_current_named_hashes


class ConfigError(Exception):
    pass


def str2bool(value):
    if value in ['yes', 'true', 'True', 'on', '1']:
        return True
    return False


# Global variable needed for the hash check
# We should try to remove it when we get to make the hash check function
# modularized
start_named_hashes = {}


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
            self.data = dict(cparser.items())
            self.load_from_ini()

            # Legacy method, will be used to pass to functions that have not yep
            # been migrated
            self.legacy_config = cparser
        except configparser.MissingSectionHeaderError:
            self.log.error("Unable to load config file {}".format(config_path))
            raise ConfigError

    def load_from_ini(self):
        """
        Loads configuration from a INI file. There are three fatal exceptions
        that can block the load
        - Missing main section
        - Missing criteria section for one of the specified candidates
        - Missing mandatory parameters
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
            "api_url"
        ]
        for param in mandatory_parameters:
            try:
                setattr(self, param, data_main[param])
            except KeyError:
                conf_ok = False
                self.log.error("Missing mandatory parameter: %s", param)

        # Mangling and derivatives
        if hasattr(self, "distro_name"):
            self.distro_name = self.distro_name.lower
        if hasattr(self, "distro_name") and hasattr(self, "distroversion"):
            self.distro = "{}{}".format(self.distroname, self.distroversion)

        # Optional parameters
        self.dry_run = str2bool(data_main['dry_run'])
        self.manifest_push = str2bool(self.get_path("main/manifest_push",
                                                    "false"))
        self.target_registries_push = str2bool(self.get_path(
            "main/target_registries_push", "true"))
        self.dlrnauth_username = self.get_path('main/username')
        self.dlrnauth_password = self.get_path("main/username")
        self.latest_hashes_count = self.get_path("main/latest_hashes_count")
        self.promotion_steps_map = self.data['promote_from']
        for target_name, candidate_name in self.promotion_steps_map.items():
            try:
                self.promotion_criteria_map = self.data[target_name]
            except KeyError:
                self.log.error("Missing criteria section for target %s",
                               target_name)
                conf_ok = False

        # Legacy parameters
        api_client = dlrnapi_client.ApiClient(host=self.api_url)
        self.api_instance = dlrnapi_client.DefaultApi(api_client=api_client)
        hashes = fetch_current_named_hashes(self.release,
                                            self.promotion_steps_map,
                                            self.api_instance)
        global start_named_hashes
        start_named_hashes = hashes

        if not conf_ok:
            raise ConfigError("Error(s) in configuration")

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
