"""
THis file contains classes that deal with configuration of the staging
environment
"""
import logging
import os
import pprint
import yaml

from stage_dlrn import expand_dlrn_config
from config import PromoterConfigBase


class StageConfig(object):
    """
    This creates a shareable configuration object that can be passed to all
    the classes in the staging environment
    It also contains default values used in the cli arguments
    """

    log = logging.getLogger("promoter-staging")

    # Used mainly for passing defaults to argparse
    defaults = type("Defaults", (), {
        'scenes': [
            "dlrn",
            "overcloud_images",
            "containers",
            "registries",
        ],
        'promoter_user': os.environ.get("USER", "centos"),
        'db_data_file': "single-pipeline.yaml",
        'stage_config_file': "stage-config.yaml",
        'stage_info_file': "/tmp/stage-info.yaml",
        'promoter_config_file': "CentOS-7/master.ini",
    })

    def __init__(self, source=None, overrides=None):
        """
        orchestrates the various filter on the configuration parameters,
        and finally load configuration dict to the object
        :param source: From where to copy config options, it can either be a
        dictionary with config options as keys, or a str with a path to a
        config file.
        :param overrides: a namespace object containing command line arguments
        """
        """
        This loads the yaml configuration file containing information on paths
        and distributions to stage
        Also adds some static informations
        """

        # config Sections
        self.dlrn = None
        self.registries = None
        self.containers = None
        self.main = None
        self.overcloud_images = None

        self.code_root = os.path.dirname(os.path.abspath(__file__))
        # Initial load
        _config = self.load_from_source(source)

        # Additional filters to configuration
        _config = self.handle_overrides(_config, overrides)
        _config = self.convert_paths(_config)
        _config = self.expand_config(_config)
        # Fill sections
        for section_name, section_data in _config.items():
            setattr(self, section_name, section_data)

    def load_from_source(self, source):
        """
        Create the _config dict from various configuration sources
        :param source: From where to copy config options, it can either be a
        dictionary with config options as keys, or a str with a path to a
        config file.
        :param source:
        :return: the initial _config dict
        """
        _config = {}
        if source is None:
            # with empty source we default with default config file
            source = self.defaults.stage_config_file
        if type(source) == str:
            # A str source is a file name in yaml to load
            config_path = os.path.join(self.code_root, source)
            with open(config_path) as cf:
                _config = yaml.safe_load(cf)
        elif type(source) == dict:
            _config = source
        else:
            raise Exception("No config source specified")

        return _config

    def expand_config(self, _config):
        """
        Extracts and manipuilate derivative data from specified config
        options and db data
        :param _config: the config dict
        :return: the expanded _config dict
        """
        distro = "{}{}".format(_config['main']['distro_name'],
                               _config['main']['distro_version'])
        _config['main']['distro'] = distro

        default_repo_host = "trunk.rdoproject.org"
        if 'repo_url' not in _config:
            repo_url = "https://{}/{}-{}".format(default_repo_host,
                                                 distro,
                                                 _config['main']['release'])
        _config['dlrn']['repo_url'] = repo_url

        # DB data are the basis for all the environment
        # not just for db injection, they contain the commit info
        # on which the entire promotion is based.
        db_data_path = _config['dlrn']['server']['db_data_file']
        with open(db_data_path) as db_data_file:
            _config['dlrn']['server']['db_data'] = yaml.safe_load(db_data_file)

        # If commits do not contain the component key or if it's None
        # We are in the single pipeline, otherwise we are in the integration
        # pipeline
        # WE CANNOT mix component commits with non-components
        db_commits = _config['dlrn']['server']['db_data']['commits']
        components_mode = bool(db_commits[0].get('component', None))
        for commit in db_commits:
            if bool(commit.get('component', None)) != components_mode:
                raise Exception("Mixed component/non-component commits"
                                " in db data")
        _config['main']['components_mode'] = components_mode

        # create a temporary config file
        log_name = "{}-{}.log".format(_config['main']['distro'],
                                      _config['main']['release'])
        _config['main']['log_file'] = \
            os.path.join(_config['main']['stage_root'], log_name)

        # Let Dlrn scene controller handle its own configuration
        _config = expand_dlrn_config(_config)

        # Hardcode base images into containers suffixes
        base_images = ['base', 'openstack-base']
        _config['containers']['images-suffix'] = \
            base_images + _config['containers']['images-suffix']

        # Expand containers namespace
        _config['containers']['namespace'] = \
            "{}{}".format(_config['containers']['namespace_prefix'],
                          _config['main']['release'])

        return _config

    def handle_overrides(self, _config, overrides):
        """
        replaces selected config variables with values coming from command
        line arguments.
        :param _config: The starting _config dict
        :param overrides: A namespace object with config overrides.
        :return: the overridden _config dict
        """

        main_overrides = ('scenes', 'dry_run', 'promoter_user',
                          'promoter_config_file')
        for override in main_overrides:
            try:
                attr = getattr(overrides, override)
                _config['main'][override] = attr
            except AttributeError:
                self.log.debug("Main config key %s not overridden" % override)
            except TypeError:
                # overrides exists but it's None
                pass

        # load main config parameters from the promoter conf we are trying to
        # emulate
        _config['main']['promoter_config_file'] = \
            os.path.join(self.code_root, "config",
                         _config['main']['promoter_config_file'])
        promoter_config = \
            PromoterConfigBase(config_file=_config['main'][
                'promoter_config_file'])
        _config['main']['distro_name'] = promoter_config.distro_name
        _config['main']['distro_version'] = promoter_config.distro_version
        _config['main']['release'] = promoter_config.release

        try:
            _config['dlrn']['server']['db_data_file'] = overrides.db_data_file
        except AttributeError:
            pass

        return _config

    def convert_paths(self, _config):
        """
        Converts all the relative paths in config into absolute paths
        :param _config: the _config dict
        :return: The converted  config dict
        """
        stage_root = _config['main']['stage_root']

        # DLRN
        dlrn_root = os.path.join(stage_root, _config['dlrn']['server']['root'])
        _config['dlrn']['server']['root'] = dlrn_root

        repo_root = os.path.join(dlrn_root,
                                 _config['dlrn']['server']['repo_root'])
        _config['dlrn']['server']['repo_root'] = repo_root

        # DLRN - db data file
        dbdata_dir = "stage_dbdata"
        db_data_file = os.path.join(self.code_root, dbdata_dir,
                                    _config['dlrn']['server']['db_data_file'])
        _config['dlrn']['server']['db_data_file'] = db_data_file

        # DLRN- runtime server sqlite db file
        db_file = os.path.join(dlrn_root,
                               _config['dlrn']['server']['db_file'])
        _config['dlrn']['server']['db_file'] = db_file

        # Ovecloud images paths
        images_root = os.path.join(stage_root,
                                   _config['overcloud_images']['root'])
        _config['overcloud_images']['root'] = images_root

        # Containers paths
        containers_root = os.path.join(stage_root,
                                       _config['containers']['root'])
        _config['containers']['root'] = containers_root
        containers_yaml_path = \
            os.path.join(containers_root,
                         _config['containers']['containers_yaml'])
        _config['containers']['containers_yaml'] = containers_yaml_path

        return _config
