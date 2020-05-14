'''
Converts a single file from ini to yaml mainitaining the data format.
'''


try:
    # Python 3 import
    import configparser as ini_parser
except ImportError:
    # Python 2 import
    import ConfigParser as ini_parser

import logging
import os
import yaml
import sys

def main(config_path_ini=None):
    log = logging.getLogger("converter")

    if config_path_ini == None:
        config_path_ini = sys.argv[1]
    cparser = ini_parser.ConfigParser(allow_no_value=True)
    log.info("Reading INI config file %s", config_path_ini)
    cparser.read(config_path_ini)

    config_path_ini
    config_path, __ = os.path.splitext(config_path_ini)
    config_path_yaml = "{}.yaml".format(config_path)

    config_ini = dict(cparser.items())
    config_main_yaml = yaml.safe_dump(
        { 'main': dict(config_ini['main'].items()) }
    )
    config_promote_yaml = yaml.safe_dump(
        { 'promote_from': dict(config_ini['promote_from'].items()) }
    )
    config_tripleo_yaml = ""
    try:
        config_tripleo_yaml = yaml.safe_dump(
            { 'current-tripleo' : dict(config_ini['current-tripleo'].items()) }
        )
    except KeyError:
        pass
    config_rdo_yaml = ""
    try:
        config_rdo_yaml = yaml.safe_dump(
            { 'current-tripleo-rdo' : dict(config_ini['current-tripleo-rdo'].items()) }
        )
    except KeyError:
        pass
    config_staging_yaml = ""
    try:
        config_staging_yaml = yaml.safe_dump(
            { 'tripleo-ci-staging-promoted' : dict(config_ini['tripleo-ci-staging-promoted'].items()) }
        )
    except KeyError:
        pass

    log.info("Writing yaml config file %s", config_path_yaml)
    with open(config_path_yaml, "w") as config_file_yaml:
        config_file_yaml.write(config_main_yaml)
        config_file_yaml.write(config_promote_yaml)
        config_file_yaml.write(config_tripleo_yaml)
        config_file_yaml.write(config_rdo_yaml)
        config_file_yaml.write(config_staging_yaml)

    return config_path_yaml

if __name__ == "__main__":
    main()
