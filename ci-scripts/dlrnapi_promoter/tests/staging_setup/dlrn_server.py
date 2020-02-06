import logging
import os
import pprint
import shutil
import socket
import subprocess
import time
import yaml

from dlrn import db as dlrn_db
from dlrn import utils
from dlrn_interface import (DlrnClient, DlrnClientConfig, DlrnHash,
                            DlrnCommitDistroHash)
from inspect import cleandoc
from sqlalchemy import exc as sql_a_exc
from string import Template

try:
    # In python 2 ConnectionRefusedError is not a builtin
    from socket import error as ConnectionRefusedError
except ImportError:
    pass

def conditional_run(orig_function):
    def new_function(*args, **kwargs):
        if not args[0].config.main['dry_run']:
            orig_function(*args, **kwargs)
    return new_function


dlrn_staging_server = '''
#!/usr/bin/env python
from dlrn.api import app
app.run(debug=True, port=58080)
'''

versions_csv = '''openstack-tripleo-common,https://git.openstack.org/openstack/tripleo-common,c57d2420a8435af7813b44a772df98c8c444f990,https://github.com/rdo-packages/tripleo-common-distgit.git,25fbd3fa6d8ea905e0b6ae386780f0203d22b732,SUCCESS,1574467338,openstack-tripleo-common-11.4.0-0.20191123000336.c57d242.el7
python-tripleo-common-tests-tempest,https://git.openstack.org/openstack/tripleo-common-tempest-plugin,b6929550ca4a5b6269b4451ec2250053728b7fa2,https://github.com/rdo-packages/tripleo-common-tempest-plugin-distgit.git,7ae014d193ad00ddb5007431665a0b3347c2c94b,SUCCESS,1573236125,python-tripleo-common-tests-tempest-0.0.1-0.20191108180320.b692955.el7
'''

repo_template = '''[deloran${repo_name}]

baseurl=file://${stage_root}${distro}/${commit_dir}
'''


class DlrnStagingServer(object):

    log = logging.getLogger("promoter-staging")

    def __init__(self, config):
        self.config = config

        # Server
        self.host = self.config.dlrn['server']['host']
        self.port = self.config.dlrn['server']['port']
        self.username = self.config.dlrn['server']['username']
        self.password = self.config.dlrn['server']['password']
        self.api_url = 'http://{}:{}'.format(self.host, self.port)

        # Client
        client_config = DlrnClientConfig(dlrnauth_username = self.username,
                                         dlrnauth_password = self.password,
                                         api_url=self.api_url)

        self.client = DlrnClient(client_config)

        # Paths
        self.repo_root = self.config.dlrn['server']['repo_root']
        self.stage_root = self.config.main['stage_root']
        self.server_root = self.config.dlrn['server']['root']
        self.db_file = self.config.dlrn['server']['db_file']
        self.db_fixtures = self.config.dlrn['server']['db_fixtures']

        self.commits = self.config.dlrn['commits']
        self.pipeline_type = self.config.main['pipeline_type']
        if self.pipeline_type == "single":
            # component pipeline has no promotion predefined
            self.promotions = self.config.dlrn['promotions']
            self.rev_promotions = self.config.dlrn['rev_promotions']
        self.promotion_target = self.config.dlrn['promotion_target']

        self.release = self.config.main['release']
        self.distro = self.config.main['distro']
        self.dry_run = self.config.main['dry_run']

        self.launch_cmd = "python dlrn_staging_server.py"
        self.teardown_cmd = "pkill -f dlrn_staging_server"

        # Creates dlrn and repo dirs
        if not self.config.main['dry_run']:
            try:
                os.makedirs(self.server_root)
            except OSError:
                self.log.info("Repo root dir exists, not creating")
            try:
                os.makedirs(self.repo_root)
            except OSError:
                self.log.info("Repo root dir exists, not creating")

    def setup_repo_path(self):
        """
        CANDIDATE FOR REMOVAL
        This function should setup the repo path for the dlrnapi server
        emulating the path created during the build of a repo associated
        to an hash
        But AFAIU the dlrnapi server doesn't care if directory created or not,
        the promotion via dlrnapi will create a broken link to a directory that
        doesn't exist, but doesn't produce any error. Unless we hit some error
        we can completely ignore this part and remove this TODO(panda)
        """
        # Setting up repo path is optional
        # dlrn hash promoted via api just create a broken link
        # but we don't care.
        repo_path = "/tmp/delorean"
        # TODO(fixme) if we want to keep this we must pass dlrn_hash and
        # candidate name
        dlrn_hash = "foo"
        candidate_name = "bar"
        os.mkdir(repo_path + dlrn_hash)
        os.symlink(repo_path + dlrn_hash, candidate_name)


    @conditional_run
    def create_db(self):
        """
        Injects the fixture to the database using the existing utils
        offered by dlrn itself
        """
        # Creates db from fixtures on dlrn root dir
        self.log.debug("Injecting %s fixtures to %s", self.db_fixtures,
                       self.db_file)

        session = dlrn_db.getSession("sqlite:///%s" % self.db_file)
        try:
            utils.loadYAML(session, self.db_fixtures)
        except sql_a_exc.IntegrityError:
            self.log.info("DB is not empty, not injecting fixtures")

    @conditional_run
    def run_server(self):
        """
        Launches dlrn api server
        """
        self.log.debug("Launching DLRN server with command: '%s'",
                       self.launch_cmd)

        # Create dlrn staging server script on dlrn root dir
        dlrn_server_path = os.path.join(self.server_root,
                                        "dlrn_staging_server.py")
        with open(dlrn_server_path, "w") as dlrn_staging_script:
            dlrn_staging_script.write(dlrn_staging_server)

        # Launches the server
        working_dir = os.getcwd()
        os.chdir(self.server_root)
        try:
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
                sock.connect(('localhost', 58080))
                connected = True
            except ConnectionRefusedError:
                # retry in 1 sec
                time.sleep(1)
                timeout -= 1

        if not connected:
            raise Exception("Dlrn server not listening to port")

    def create_file_hierarchy(self):
        """
        Creates file tree, generates url for access.
            setup the repo path for the dlrnapi server emulating the
        path created during the build of a repo associated to an hash. Not
        necessary for the promotion itself, but needed for testing of other
        components
        :return:
        """
        # Complete creation of repo structure
        for commit in self.commits:
            self.create_commit_hierarchy(commit)

    def create_commit_hierarchy(self, commit):
        # The logic here is quite hard
        # We are trying to simulate the step immediately before the promotion
        # For the single pipeline, the database provide enough information
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

        # Try to understand if the fixtures refer to a single pipeline
        # or a component pipeline from the promotions format
        #

        dlrn_hash = DlrnCommitDistroHash(source=commit)

        subst_dict = {
            'distro': self.distro,
            'stage_root': self.stage_root,
        }
        if self.pipeline_type == "component":
            # To simulate a staging environment for the component
            # pipeline, we need to promote every commit to the candidate
            # name, then dlrn will do the rest
            repo_name = "-component-{}".format(commit['component'])
            rel_commit_dir = os.path.join("components",
                                          dlrn_hash.commit_dir)
        else:
            # To simulate a staging environment for the single pipeline,
            # we just need to promote every commit to its specific name.
            repo_name = ""
            rel_commit_dir = os.path.join(dlrn_hash.commit_dir)

        subst_dict['commit_dir'] = rel_commit_dir
        subst_dict['repo_name'] = repo_name

        abs_commit_dir = os.path.join(self.repo_root, rel_commit_dir)


        try:
            os.makedirs(abs_commit_dir)
        except OSError:
            pass

        self.create_additional_files(commit, abs_commit_dir, subst_dict)
        self.promote_hash(commit, rel_commit_dir)

    def promote_hash(self, commit, commit_dir):
        if self.pipeline_type == "single" \
                and commit['id'] in self.rev_promotions:
            link_path = os.path.join(self.repo_root,
                                     self.rev_promotions[commit['id']])
            try:
                os.unlink(link_path)
            except OSError:
                pass
            try:
                os.symlink(commit_dir, link_path)
            except OSError:
                self.log.error("Unable to promote dlrn hash repo")
                raise
        elif self.pipeline_type == "component":
            # in component pipeline, we are not going to simulate the creation
            # of the aggregate hash, we're going to call dlrnapi to promote
            # and let the server do its job
            hash = DlrnCommitDistroHash(source=commit)
            self.client.promote(hash, commit['name'])

    def create_additional_files(self, commit, commit_dir, subst_dict):
        template = Template(repo_template)
        repo_file = template.substitute(subst_dict)
        commits_yaml = yaml.safe_dump({'commits': [commit]})
        additional_files = {
            'versions.csv': versions_csv,
            'commits.yaml': commits_yaml,
            'delorean.repo': repo_file,
        }
        for filename, content in additional_files.items():
            file_path = os.path.join(commit_dir, filename)
            with open(file_path, "w") as file:
                file.write(content)


    def setup(self):
        """
        Calls the various steps in order
        :return: Nothing, purely procedural
        """

        self.create_db()
        self.run_server()
        self.create_file_hierarchy()

        return self.stage_info

    def teardown(self):
        if self.dry_run:
            return
        try:
            subprocess.check_call(self.teardown_cmd.split())
        except subprocess.CalledProcessError:
            self.log.warning("Cannot shut down DLRN: no"
                             " process running")
        shutil.rmtree(self.server_root)

    @property
    def stage_info(self):
        stage_info = {}
        stage_info['server'] = {
            'api_url': 'http://{}:{}'.format(self.host, self.port),
            'repo_url': 'file://{}'.format(self.repo_root),
            'username': self.username,
            'password': self.password,
            'root': self.server_root,
        }
        stage_info['promotions'] = self.config.dlrn['promotions']
        stage_info['commits'] = self.config.dlrn['commits']
        stage_info['promotion_target'] = self.promotion_target
        return stage_info

