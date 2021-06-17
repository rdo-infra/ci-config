"""
THis file contains classes that deal with configuration of the staging
environment
"""
import datetime
import logging
import os

import yaml
from promoter.config import PromoterConfig
from stage.stage_dlrn import expand_dlrn_config


class StageConfig(PromoterConfig):

    log = logging.getLogger("promoter")

    def _constructor_log_file(self):
        # create log file
        log_name = "{}{}_{}.log".format(self['distro_name'],
                                        self['distro_version'],
                                        self['release'])
        log_file = os.path.join(self['stage_root'], log_name)
        return log_file

    def _constructor_container_push_logfile(self):
        container_push_logdir = os.path.expanduser(
            self['container_push_logdir'])
        container_push_logfile = os.path.join(
            container_push_logdir,
            "%s.log" % datetime.datetime.now().strftime(
                "%Y%m%d-%H%M%S"))
        return container_push_logfile

    def _constructor_components_mode(self):
        # If commits do not contain the component key or if it's None
        # We are in the single pipeline, otherwise we are in the integration
        # pipeline
        # WE CANNOT mix component commits with non-components

        db_commits = self.dlrn['server']['db_data']['commits']
        components_mode = bool(db_commits[0].get('component', None))
        for commit in db_commits:
            if bool(commit.get('component', None)) != components_mode:
                raise Exception("Mixed component/non-component commits"
                                " in db data")
        return components_mode

    def _constructor_qcow_server(self):
        qcow_server = super(StageConfig, self)._constructor_qcow_server()
        # Ovecloud images paths

        qcow_server['root'] = os.path.join(self.stage_root, qcow_server['root'])

        return qcow_server

    def _filter_promotions(self, __):
        promotions = {
            'tripleo-ci-staging-promoted': {
                'candidate_label': 'tripleo-ci-staging',
                'criteria': {
                    'staging-job-1',
                    'staging-job-2'
                }
            }
        }

        return promotions

    def _filter_containers(self, new_container):
        # Hardcode base images into containers suffixes
        if 'base' not in new_container['images-suffix']:
            new_container['images-suffix'] = ['base'] + new_container[
                'images-suffix']

        # Expand containers namespace
        new_container['namespace'] = \
            "{}{}".format(new_container['namespace_prefix'], self.release)

        new_container['root'] = os.path.join(self.stage_root,
                                             new_container['root'])

        # TODO(gcerami) this must be taken from the versions.csv static info
        #  in an automatic way
        tripleo_commit_sha = "163d4b3b4b211358512fa9ee7f49d9fb930ecd8f"
        new_container['tripleo_commit_sha'] = tripleo_commit_sha
        temp = self._layers['environment_defaults']['containers']
        new_container['containers_list_path'] = temp['containers_list_path']

        containers_list_base = \
            os.path.join(new_container['root'],
                         new_container['containers_list_base'])
        new_container['containers_list_base'] = containers_list_base

        return new_container

    def _filter_dlrn(self, dlrn):
        dlrn_root = os.path.join(self.stage_root, dlrn['server']['root'])

        dlrn['server']['root'] = dlrn_root

        repo_root = os.path.join(dlrn_root,
                                 dlrn['server']['repo_root'])
        dlrn['server']['repo_root'] = repo_root

        # DLRN - db data file
        dbdata_dir = "stage_dbdata"
        db_data_file = os.path.join(self.script_root, dbdata_dir,
                                    dlrn['server']['db_data_file'])
        dlrn['server']['db_data_file'] = db_data_file

        # DB data are the basis for all the environment
        # not just for db injection, they contain the commit info
        # on which the entire promotion is based.
        db_data_path = dlrn['server']['db_data_file']
        with open(db_data_path) as db_data_file:
            dlrn['server']['db_data'] = yaml.safe_load(db_data_file)

        dlrn = expand_dlrn_config(dlrn)

        # DLRN- runtime server sqlite db file
        db_file = os.path.join(dlrn_root,
                               dlrn['server']['db_file'])
        dlrn['server']['db_file'] = db_file

        return dlrn
