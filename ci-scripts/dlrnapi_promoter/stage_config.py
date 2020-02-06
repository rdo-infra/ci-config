"""
This script emulates the state of the environment around promoter as it would be
just before starting a promotion process.

The promotion interacts with:
    - dlrn_api (staged locally as standalone service)
    - docker registries (staged locally with registries on different ports)
    - images server (staged locally as normal sftp via ssh)

It can setup different components independently, the list of components it
handles it's currently defined by the "components" variable

This provisioner should produce

- A database usable by dlrnapi that contains hashes, users, votes from jobs
- A hierarchy for overcloud images, so image promotion script can
  sftp to localhost and change the links accordingly
  see the overcloud_images subtree in sample/tree.txt
- A pattern file, optionally used by container-push
  playbook as a list of containers to promote see the
  overcloud_contaienrs_yaml subtree in sample/tree.txt
- a yaml file containing reusable information on what this script produced for
  the components called
- A set of images pushed to source registry, so the promoter has the container
  to pull and  push during the promotion run see sample/docker_images.txt
- A staging_environment.ini with criteria to pass to the promoter server.
  TODO(marios) remove this bit it is moved now different review ^

The tests for this script should at least check that the script produces all
the elements consistently with the samples
"""
import logging
import os
import pprint
import yaml

from stage_dlrn import expand_dlrn_config


class StageConfig(object):

    log = logging.getLogger("promoter-staging")

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
    })

    def __init__(self, source=None, overrides=None):
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
        # Extract and manipulate useful data from config and db data
        distro = "{}{}".format(_config['main']['distro_name'],
                               _config['main']['distro_version'])
        _config['main']['distro'] = distro

        # fixtures are the basis for all the environment
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

        # Let Dlrn scene controller handle its own configuration
        _config = expand_dlrn_config(_config)

        # Hardcode base images into containers suffixes
        base_images = ['base', 'openstack-base']
        _config['containers']['images-suffix'] = \
            base_images + _config['containers']['images-suffix']

        # Expand containers namespace
        _config['containers']['namespace'] = \
            "{}{}".format(_config['containers']['namespace_prefix'],
                          distro)

        return _config

    def handle_overrides(self, _config, overrides):
        # Handle overrides
        main_overrides = ('scenes', 'dry_run', 'promoter_user')
        for override in main_overrides:
            try:
                attr = getattr(overrides, override)
                _config['main'][override] = attr
            except AttributeError:
                self.log.debug("Main config key %s not overridden" % override)
            except TypeError:
                # overrides exists but it's None
                pass

        try:
            _config['dlrn']['server']['db_data_file'] = overrides.db_data_file
        except AttributeError:
            pass

        return _config

    def convert_paths(self, _config):
        # convert relative paths to absolute
        stage_root = _config['main']['stage_root']

        # DLRN
        dlrn_root = os.path.join(stage_root, _config['dlrn']['server']['root'])
        _config['dlrn']['server']['root'] = dlrn_root

        repo_root = os.path.join(dlrn_root,
                                 _config['dlrn']['server']['repo_root'])
        _config['dlrn']['server']['repo_root'] = repo_root

        dbdata_dir = "stage_dbdata"
        db_data_file = os.path.join(self.code_root, dbdata_dir,
                                    _config['dlrn']['server']['db_data_file'])
        _config['dlrn']['server']['db_data_file'] = db_data_file

        db_file = os.path.join(dlrn_root,
                               _config['dlrn']['server']['db_file'])
        _config['dlrn']['server']['db_file'] = db_file

        # Ovecloud images
        images_root = os.path.join(stage_root,
                                   _config['overcloud_images']['root'])
        _config['overcloud_images']['root'] = images_root

        containers_root = os.path.join(stage_root,
                                       _config['containers']['root'])
        _config['containers']['root'] = containers_root
        containers_yaml_path = \
            os.path.join(containers_root,
                         _config['containers']['containers_yaml'])
        _config['containers']['containers_yaml'] = containers_yaml_path

        return _config
