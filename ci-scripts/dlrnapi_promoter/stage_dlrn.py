"""
This files contains classes and function that deal with the creation of a
staging dlrn server and the relative repository
"""
import copy
import logging
import os
import pprint
import shutil
import socket
import subprocess
import time
import yaml

try:
    import ConfigParser as ini_parser
except ImportError:
    import configparser as ini_parser

from dlrn import db as dlrn_db
from dlrn import utils
from dlrn_client import (DlrnClient, DlrnClientConfig)
from dlrn_hash import DlrnCommitDistroHash
from sqlalchemy import exc as sql_a_exc
from string import Template

try:
    # In python 2 ConnectionRefusedError is not a builtin
    from socket import error as ConnectionRefusedError
except ImportError:
    pass


def conditional_run(orig_function):
    """
    A decorator to run the wrapped function only when the dry_run variable
    is set to True
    :param orig_function:  The function to run only when not in dry run
    :return: The wrapped function
    """
    def new_function(*args, **kwargs):
        if not args[0].config.main['dry_run']:
            orig_function(*args, **kwargs)
    return new_function


# script to run staging dlrn server
dlrn_staging_server = '''#!/usr/bin/env python
from dlrn.api import app
app.run(debug=True, port=58080)
'''

# Static version.csv to retrieve the tripleo-common git sha
versions_csv = '''openstack-tripleo-common,https://git.openstack.org/openstack/tripleo-common,c57d2420a8435af7813b44a772df98c8c444f990,https://github.com/rdo-packages/tripleo-common-distgit.git,25fbd3fa6d8ea905e0b6ae386780f0203d22b732,SUCCESS,1574467338,openstack-tripleo-common-11.4.0-0.20191123000336.c57d242.el7
python-tripleo-common-tests-tempest,https://git.openstack.org/openstack/tripleo-common-tempest-plugin,b6929550ca4a5b6269b4451ec2250053728b7fa2,https://github.com/rdo-packages/tripleo-common-tempest-plugin-distgit.git,7ae014d193ad00ddb5007431665a0b3347c2c94b,SUCCESS,1573236125,python-tripleo-common-tests-tempest-0.0.1-0.20191108180320.b692955.el7
'''

# template for the single pipeline delorean.repo to put in
# staging repo
repo_template = '''[delorean${repo_name}]

baseurl=file://${repo_root_files}/${commit_dir}
'''


def expand_dlrn_config(_config):
    """
    Called by StageConfig.expand_config to expand the dlrn configuration part
    :param _config: The config dict
    :return: the expanded config dict, with dlrn information
    """
    _config['dlrn']['promotions'] = {}
    db_commits = _config['dlrn']['server']['db_data']['commits']
    # Every third commit in the group of commits, will be the last to
    # promote that name, and so it will be the one tied to the aggregate
    # hash that we'll have to promote
    promotions_map = _config['dlrn']['server']['db_data'][
        'promotions_map']

    # expands db commit information with associated promotions and full_hashes
    # and create promotions map
    commits = []
    for index, db_commit in enumerate(db_commits):
        commit = copy.deepcopy(db_commit)
        promotion_name, promotion_alias = \
            promotions_map.get(index, (None, None))
        if promotion_name is not None:
            commit['name'] = promotion_name
            commit['full_hash'] = DlrnCommitDistroHash(source=commit).full_hash
        if promotion_alias is not None:
            _config['dlrn']['promotions'][promotion_alias] = \
                commit
        commits.append(commit)

    _config['dlrn']['commits'] = commits

    # Create reverse promotion map from promotions map
    _config['dlrn']['rev_promotions'] = {}
    for promotion_alias, commit in _config['dlrn']['promotions'].items():
        _config['dlrn']['rev_promotions'][commit['id']] = promotion_alias

    return _config


class StagingRepo(object):
    """
    This handles the local staging repo subtree
    """
    log = logging.getLogger("promoter-staging")

    def __init__(self, config):
        """
        like many inits around the code, this loads the config and create
        shortcuts for the used configuration parameters
        This init also creates the base root dir of the repo subtree
        :param config: The global stage config
        """
        self.config = config
        self.commits = self.config.dlrn['commits']
        self.release = self.config.main['release']
        self.distro = self.config.main['distro']
        self.dry_run = self.config.main['dry_run']
        self.server_root = self.config.dlrn['server']['root']
        self.repo_root_server = self.config.dlrn['server']['repo_root']
        self.distro_combo = "{}-{}".format(self.distro, self.release)
        self.repo_root_files = os.path.join(self.server_root,
                                            self.distro_combo)
        self.components_mode = self.config.main['components_mode']
        self.promotions = self.config.dlrn['promotions']
        self.rev_promotions = self.config.dlrn['rev_promotions']
        self.rel_commit_dir = None

        if not self.dry_run:
            try:
                os.makedirs(self.repo_root_server)
            except OSError:
                pass
            try:
                os.symlink(self.repo_root_server, self.repo_root_files)
            except OSError:
                pass

    def create_commit_hierarchy(self, commit):
        """
        Every single pipeline commit or component commit has a hierarchy of
        files inside the DLRN repo.
        This sets up templates substitution variables and calls the method that
        will create all the additional files in the hierarchy for the commit
        :return: the location of the commit repo
        """
        # Complete creation of repo structure
        # The logic here is quite hard
        # We are trying to simulate the step immediately before the promotion
        # For the single pipeline, the database provide    enough information
        # For component pipeline, many things are done by dlrn build process,
        # and the database information is incomplete. For example, there is no
        # way to associate a commit to a component, and no way to retrieve
        # the list of commits that promoted to a specific name, the aggregate
        # promotion refers only to the last commit.
        # The api gives a bit more information, but the staging environment
        # creation comes before any api activation
        # To simplify test procedures we are going to pass two different
        # fixture files with db values specific to the case
        # One will be used for single pipeline
        # The other will be used for component pipeline

        dlrn_hash = DlrnCommitDistroHash(source=commit)

        subst_dict = {
            'distro': self.distro,
            'repo_root_files': self.repo_root_files,
        }
        # sets template subst variables
        if self.components_mode:
            repo_name = "-component-{}".format(commit['component'])
            self.rel_commit_dir = os.path.join("component",
                                               commit['component'],
                                               dlrn_hash.commit_dir)
        else:
            repo_name = ""
            self.rel_commit_dir = os.path.join(dlrn_hash.commit_dir)

        subst_dict['commit_dir'] = self.rel_commit_dir
        subst_dict['repo_name'] = repo_name

        abs_commit_dir = os.path.join(self.repo_root_files, self.rel_commit_dir)

        try:
            os.makedirs(abs_commit_dir)
        except OSError:
            pass

        self.create_additional_files(commit, abs_commit_dir, subst_dict)

        return self.repo_root_files

    def staged_promotion(self, commit):
        """
        Creates symlinks to simulate a dlrn promotion in the repository
        Valid only for the single pipeline or component commit promotion.
        :param commit: A dict with info of the commit to promote
        :return: None
        """
        target_label = commit['name']
        dlrn_hash = DlrnCommitDistroHash(source=commit)
        link_path = os.path.join(self.repo_root_files,
                                 target_label)
        try:
            os.unlink(link_path)
        except OSError:
            pass
        try:
            os.symlink(self.rel_commit_dir, link_path)
        except OSError:
            self.log.error("Staged promotion for single pipeline commit: "
                           "Unable to promote dlrn hash '{}' to {}"
                           "".format(dlrn_hash, target_label))
            raise

    @staticmethod
    def create_additional_files(commit, commit_dir, subst_dict):
        """
        The commit hierarchy is not complete without three additional files:
        - the commits.yaml with commit information
        - the versions.csv with information with git sha of the packages
        - delorean.repo RPM repo file
        :param commit: The commit to create files for
        :param commit_dir: The dir in which to create the files
        :param subst_dict: The substitution dicionary to use with the templates
        :return: None
        """
        template = Template(repo_template)
        repo_file = template.substitute(subst_dict)
        commit_yaml = yaml.safe_dump({'commits': [commit]})
        additional_files = {
            'versions.csv': versions_csv,
            'commit.yaml': commit_yaml,
            'delorean.repo': repo_file,
        }
        for filename, content in additional_files.items():
            file_path = os.path.join(commit_dir, filename)
            with open(file_path, "w") as file:
                file.write(content)


class DlrnStagingServer(object):
    """
    Orchestrates the life of the DLRN server. DB data injection, run, kill.
    """

    log = logging.getLogger("promoter-staging")

    def __init__(self, config):
        """
        like many inits around the code, this loads the config and create
        shortcuts for the used configuration parameters
        This init also contains a configuration file for the server.
        :param config: The global stage config
        """
        self.config = config

        # General
        self.release = self.config.main['release']
        self.distro = self.config.main['distro']
        self.dry_run = self.config.main['dry_run']

        # Server
        self.host = self.config.dlrn['server']['host']
        self.port = self.config.dlrn['server']['port']
        self.username = self.config.dlrn['server']['username']
        self.password = self.config.dlrn['server']['password']
        self.api_url = 'http://{}:{}'.format(self.host, self.port)

        # Client
        client_config = DlrnClientConfig(dlrnauth_username=self.username,
                                         dlrnauth_password=self.password,
                                         api_url=self.api_url)

        self.client = DlrnClient(client_config)

        # Paths
        self.repo_root = self.config.dlrn['server']['repo_root']
        self.staging_repo = StagingRepo(self.config)
        self.repo_root_files = self.staging_repo.repo_root_files
        self.stage_root = self.config.main['stage_root']
        self.server_root = self.config.dlrn['server']['root']
        self.db_file = self.config.dlrn['server']['db_file']
        self.db_data = self.config.dlrn['server']['db_data_file']

        self.components_mode = self.config.main['components_mode']
        self.commits = self.config.dlrn['commits']
        self.promotions = self.config.dlrn['promotions']
        self.rev_promotions = self.config.dlrn['rev_promotions']
        # project.conf for DLRN server using component mode
        # There is no way to use the default configuration an just override the
        # use_components variable we need to change. So we have it all here.
        if self.components_mode:
            project_conf = dict(
                datadir="./data",
                scriptsdir="./scripts",
                configdir="",
                baseurl="http://trunk.rdoproject.org/centos7/",
                distro="rpm-master",
                source="master",
                target="centos",
                smtpserver="",
                reponame="delorean",
                templatedir="./dlrn/templates",
                project_name="RDO",
                maxretries="3",
                pkginfo_driver="dlrn.drivers.rdoinfo.RdoInfoDriver",
                build_driver="dlrn.drivers.mockdriver.MockBuildDriver",
                tags="",
                rsyncdest="",
                rsyncport="22",
                workers="1",
                gerrit_topic="rdo-FTBFS",
                database_connection="sqlite:///commits.sqlite",
                fallback_to_master="1",
                nonfallback_branches="^master$,^rpm-master$",
                release_numbering="0.date.hash",
                custom_preprocess="",
                include_srpm_in_repo="true",
                keep_changelog="false",
                allow_force_rechecks="false",
                use_components="true",
            )
            self.project_conf = ini_parser.ConfigParser(defaults=project_conf)
            self.project_ini_path = os.path.join(self.server_root,
                                                 "projects.ini")

        self.promotion_target = self.config.dlrn['promotion_target']
        self.launch_cmd = "python dlrn_staging_server.py"
        self.http_launch_cmd = "/usr/sbin/lighttpd -f ./lighttpd.conf"
        self.teardown_cmd = "pkill -f dlrn_staging_server"
        self.http_teardown_cmd = "pkill -f {}".format(self.launch_cmd)

    @conditional_run
    def create_db(self):
        """
        Injects the database initial tables to the database using the existing
        utils offered by dlrn itself
        :return: None
        """
        self.log.debug("Injecting %s data to %s", self.db_data,
                       self.db_file)

        session = dlrn_db.getSession("sqlite:///%s" % self.db_file)
        try:
            utils.loadYAML(session, self.db_data)
        except sql_a_exc.IntegrityError:
            self.log.info("DB is not empty, not injecting data")

    @conditional_run
    def run_server(self):
        """
        Sets up the DLRN server working dir with launch script and
        configuration files, then launches the server
        :return: None
        """
        self.log.debug("Launching DLRN server with command: '%s'",
                       self.launch_cmd)

        # Create dlrn staging server script on dlrn root dir
        dlrn_server_path = os.path.join(self.server_root,
                                        "dlrn_staging_server.py")
        with open(dlrn_server_path, "w") as dlrn_staging_script:
            dlrn_staging_script.write(dlrn_staging_server)

        # Create server configuration in project.ini
        # It'optional for the single pipeline, but needed for the component
        # as we need to change the use_components variable
        if self.components_mode:
            with open(self.project_ini_path, 'w') as config_file:
                self.project_conf.write(config_file)

        # Launches the server
        working_dir = os.getcwd()
        os.chdir(self.server_root)
        try:
            # TODO: redirect stdout to logs
            subprocess.Popen(self.launch_cmd.split())
        except OSError:
            self.log.error("Cannot launch DLRN server: requirements missing")
            raise
        os.chdir(working_dir)

        # Wait until server port is available before moving on
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        timeout = 5
        connected = False
        while timeout > 0 and not connected:
            try:
                sock.connect((self.host, self.port))
                connected = True
            except ConnectionRefusedError:
                # retry in 1 sec
                time.sleep(1)
                timeout -= 1

        if not connected:
            raise Exception("Dlrn server not listening to port")

    def promote_aggregate(self, commit, promotion_alias):
        """
        In the integration pipeline, we are not going to simulate the
        creation of the aggregate hash repo subtree with templates.
        That would mean replicating a lot of DLRN server code. So we use
        the server itself, pointing to the right top dir of the subtree
        and feeding it with component promotions
        :param commit: A dict with the commit information
        :param promotion_alias: The alias in the promotions map to get to the
        actual target_label
        :return:
        """
        dlrn_hash = DlrnCommitDistroHash(source=commit)
        self.client.promote(dlrn_hash, commit['name'],
                            create_previous=False)
        promotion_hash = self.client.fetch_promotions_from_hash(
            dlrn_hash, count=1)
        # For aggregate, the promotion map we need contains promotion_hashes
        # not the commit hashes, so we overwrite the existing map
        # and add the promotion alias to the commit
        if promotion_alias is not None:
            promotion_dict = promotion_hash.dump_to_dict()
            promotion_dict['name'] = commit['name']
            promotion_dict['full_hash'] = promotion_hash.full_hash
            self.promotions[promotion_alias] = promotion_dict
            self.rev_promotions[commit['id']] = promotion_alias
        # Since the aggregate hashes are dynamically created, the ci
        # votes also need to be dynamically generated
        # We vote for a single job for every aggregate
        self.client.vote(promotion_hash, "staging-job-1",
                         "http://nowhe.re", True)
        # Then we vote for the second job in the criteria also for promotion
        # candidate, so it will have all required votes.
        if promotion_alias == 'promotion_candidate':
            self.client.vote(promotion_hash, "staging-job-2",
                             "http://nowhe.re", True)
        # if we promote too fast, it may happen that two hashes have the same
        # timestamp, which will break the simulation of a normal sequence of
        # builds
        # Wait 1 second to be sure that the next promotion has a different
        # timestamp
        time.sleep(1)

    def setup(self):
        """
        Orchestrates the various methods. Calling in order:
        - root dir creation
        - db data injection
        - server launch
        - Hashes promotions
        :return: A dict with dlrn stage info
        """

        # Creates dlrn and repo dirs
        if not self.config.main['dry_run']:
            try:
                os.makedirs(self.server_root)
            except OSError:
                self.log.info("Repo root dir exists, not creating")

        self.create_db()
        self.run_server()
        for commit in self.commits:
            self.repo_root_files = \
                self.staging_repo.create_commit_hierarchy(commit)

            promotion_alias = self.rev_promotions.get(commit['id'], None)
            if not self.components_mode and promotion_alias is not None:
                self.staging_repo.staged_promotion(commit)
            if self.components_mode:
                # method above can promote the commit/distro hash in repo
                # directly creating links to commit dir
                # But in case of aggregate promotion, interacting with the
                # hierarchy is not enough
                self.promote_aggregate(commit, promotion_alias)

        return self.stage_info

    def teardown(self, __):
        """
        Cleans up resource created by staging DLRN server and repo
        Kills the server and removes the dlrn tree
        :param __: An unused parameter useful for other teardown methods
        :return: None
        """
        if self.dry_run:
            return

        self.log.info("Shutting down DLRN server")
        try:
            subprocess.check_call(self.teardown_cmd.split())
        except subprocess.CalledProcessError:
            self.log.warning("Cannot shut down DLRN: no"
                             " process running")
        self.log.info("Removing dlrn server root dir")
        shutil.rmtree(self.server_root)

    @property
    def stage_info(self):
        """
        Property that returns the dict with info on the created DLRN stage
        :return: A dict with useful info
        """
        stage_info = {
            'server': {
                'api_url': 'http://{}:{}'.format(self.host, self.port),
                'repo_url': 'file://{}'.format(self.repo_root_files),
                'username': self.username,
                'password': self.password,
                'root': self.server_root,
            },
            'promotions': self.promotions,
            'commits': self.commits,
            'promotion_target': self.promotion_target
        }

        return stage_info
