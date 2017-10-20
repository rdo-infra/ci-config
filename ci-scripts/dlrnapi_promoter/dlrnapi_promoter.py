#!/usr/bin/env python

from __future__ import print_function
from datetime import datetime
from sets import Set
import ConfigParser
import logging
import logging.handlers
import os
import subprocess
import sys

from dlrnapi_client.rest import ApiException
import dlrnapi_client

class PromotionSkip(Exception):
    pass
class PromotionError(Exception):
    pass

class Log(object):

    def __init__(self, targetlist=["console"]):
        self.targetlist = targetlist

    def setup(self, log_file=None):
        '''Setup logging for the script'''
        logger = logging.getLogger('promoter')
        logger.setLevel(logging.DEBUG)
        logformat = '%(asctime)s %(process)d %(levelname)-8s %(name)s %(message)s'
        log_formatter = logging.Formatter(logformat)
        if "file" in self.targetlist and log_file is not None: 
            log_handler = logging.handlers.WatchedFileHandler(
                os.path.expanduser(log_file))
            log_handler.setFormatter(log_formatter)
            logger.addHandler(log_handler)
        if "console" in self.targetlist:
            log_handler = logging.StreamHandler()
            log_handler.setFormatter(log_formatter)
            logger.addHandler(log_handler)
        self._logger = logger
        self.log_header = ""

    def set_header(self, log_header):
        self.log_header = log_header + " "

    def unset_header(self):
        self.log_header = ""

    def info(self, msg, *args, **kwargs):
        hdr_msg = self.log_header + msg
        self._logger.info(hdr_msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        hdr_msg = self.log_header + msg
        self._logger.warning(hdr_msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        hdr_msg = self.log_header + msg
        self._logger.debug(hdr_msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        hdr_msg = self.log_header + msg
        self._logger.error(hdr_msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        hdr_msg = self.log_header + msg
        self._logger.critical(hdr_msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        hdr_msg = self.log_header + msg
        self._logger.exception(hdr_msg, *args, **kwargs)

class Config(object):

    def __init__(self, logger, config_file):
        self.file_path = config_file
        self.parser = ConfigParser.SafeConfigParser(allow_no_value=True)
        self.logger = logger
        self.parser.read(config_file)
        self.log_file = self.parser.get('main', 'log_file')
        self.logger.setup(log_file=self.log_file)
        self.api_url = self.parser.get('main', 'api_url')
        self.dry_run = self.parser.getboolean('main', 'dry_run')
        self.username = self.parser.get('main', 'username')
        self.release = self.parser.get('main', 'release')
        self.containers_builder = self.parser.get('main', 'containers_builder')

        self.password = os.getenv('DLRNAPI_PASSWORD', None)
        if self.password is None:
            self.logger.warning('DLRNAPI_PASSWORD env variable is missing or empty, '
                           'promotion attempt will fail!')

        # load the promotion requirements
        self.promotions = {}
        candidates = {}
        jobs = {}
        builders = {}
        for pair in self.parser.items('targets:candidates'):
            target, candidate = pair
            candidates[target] = candidate

        for section in self.parser.sections():
            if 'jobs_required/' in section:
                target = section.replace('jobs_required/', "")
                jobs[target] = self.parser.options(section)
            
        for target, candidate in candidates.iteritems():
            self.promotions[target] = {}
            self.promotions[target]['candidate'] = candidate
            try:
                self.promotions[target]['jobs'] = jobs[target]
            except KeyError:
                self.logger.error("missing config section: jobs_required/%s" % (target))
                raise

        logger.debug('Attempting to promote these DLRN links: %s',
                     candidates.values())

        logger.debug('Promotion requirements loaded: %s', jobs)

class DlrnHash(dict):

    def __init__(self, source=None):
        if source is not None:
            self.commit_hash = source.commit_hash
            self.distro_hash = source.distro_hash
        else:
            self.commit_hash = ""
            self.distro_hash = ""

    def __eq__(self, other):
        return self.commit_hash == other.commit_hash and self.distro_hash == other.distro_hash
    
    def __str__(self):
        return "commit: %s, distro: %s" % (self.commit_hash, self.distro_hash)

    @property
    def full_hash(self):
        return '{0}_{1}'.format(self.commit_hash, self.distro_hash[:8])

    @property
    def short_hash(self):
        return '{0}_{1}'.format(self.commit_hash[:8], self.distro_hash[:8])

class DlrnApi(object):

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        # This way of preparing parameters and configuration is copied
        # directly from dlrnapi CLI and ansible module
        self.hashes_params = dlrnapi_client.PromotionQuery()
        self.jobs_params = dlrnapi_client.Params2()
        self.promote_params = dlrnapi_client.Promotion()
        dlrnapi_client.configuration.password = self.config.password
        dlrnapi_client.configuration.username = self.config.username
        self.api_client = dlrnapi_client.ApiClient(host=config.api_url)
        self.api_instance = dlrnapi_client.DefaultApi(api_client=self.api_client)
        logger.info('Using API URL: %s', self.api_client.host)
       
    def fetch_hashes(self, promote_name):
        '''Get the commit and distro hashes for a specific promotion link'''
        self.hashes_params.promote_name = promote_name
        try:
            api_response = self.api_instance.api_promotions_get(self.hashes_params)
        except ApiException:
            self.logger.error('Exception when calling api_promotions_get: %s',
                         ApiException)
            return None
        try:
            return DlrnHash(source=api_response[0])
        except IndexError:
            return None

    def fetch_jobs(self, dlrn_hash):
        '''Fetch the successfully finished jobs for a specific DLRN hash'''
        self.jobs_params.commit_hash = dlrn_hash.commit_hash
        self.jobs_params.distro_hash = dlrn_hash.distro_hash
        self.jobs_params.success = str(True)

        try:
            api_response = self.api_instance.api_repo_status_get(self.jobs_params)
        except ApiException:
            logger.error('Exception when calling api_repo_status_get: %s',
                         ApiException)
            return None
        self.logger.debug('Successful jobs for candidate:')

        jobs = {}
        for result in api_response:
            self.logger.debug('%s at %s, logs at %s', result.job_id,
                         datetime.fromtimestamp(result.timestamp).isoformat(),
                         result.url)
            jobs[result.job_id] = result.url
       
        return jobs

    def get_container_job(self, new_hashes):
        pass

    def promote_link(self, dlrn_hash, promote_name):
        '''Promotes a set of hash values as a named link using DLRN API'''
        params = dlrnapi_instance.Promotion()
        params.commit_hash = dlrn_hash.commit_hash
        params.distro_hash = dlrn_hash.distro_hash
        params.promote_name = promote_name
        if self.config.dry_run:
            self.logger.info('DRY RUN: promotion conditions satisfied, '
                        'skipping promotion of %s to %s (old: %s, new: %s)',
                        candidate, target, current_hashes, new_hashes)
            return
        
        try:
            #self.api_instance.api_promote_post(params)
            self.logger.info("promoted")
        except ApiException:
            logger.error('Exception when calling api_promote_post: %s',
                         ApiException)
            raise

class Promoter(object):

    def __init__(self, config_file_path):
        self.logger = Log()
        self.config = Config(self.logger, config_file_path)
        relpath = "ci-scripts/dlrnapi_promoter"
        self.script_root = os.path.abspath(sys.path[0]).replace(relpath,"")
        self.images_promote_script = self.script_root + 'ci-scripts/promote-images.sh'
        self.containers_promote_playbook = (
            self.script_root + 'ci-scripts/container-push/container-push.yml'
        )
        # setup the API connection
        self.dlrnapi = DlrnApi(self.config, self.logger)

        try:
            git_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                               cwd=os.path.abspath(sys.path[0]))
            self.logger.info('Current git hash of repo containing the promoter '
                        'script: %s', git_hash.strip())
        except OSError:
            self.logger.warning('Failed to get the current git repo hash, check if '
                         'git is installed.')
        except subprocess.CalledProcessError:
            self.logger.warning('Failed to get the current git repo hash, probably not '
                         'running inside a git repository.')

    def tag_containers(new_hashes, promote_name):
        container_list_url = self.dlrnapi.get_container_job(new_hashes)
        env = os.environ
        env['IMAGES_LIST_URL'] = container_list_url
        env['RELEASE'] = self.config.release
        env['COMMIT_HASH'] = new_hashes['commit_hash']
        env['DISTRO_HASH'] = new_hashes['distro_hash']
        env['FULL_HASH'] = new_hashes['full_hash']
        env['PROMOTE_NAME'] = promote_name
        env['SCRIPT_ROOT'] = self.script_root
        commit_hash = new_hashes['commit_hash']
        command = 'ansible-playbook'
        if self.config.dry_run:
            command.append("--check")
        command.append(self.containers_promote_playbook)

        try:
            self.logger.info('Promoting the container images for dlrn hash %s on '
                        '%s to %s', commit_hash, self.config.release, promote_name)
            output = subprocess.check_output(command, env=env,
                                             stderr=subprocess.STDOUT)
            for line in output.split("\n"):
                self.logger.info(line)
        except subprocess.CalledProcessError as ex:
            self.logger.error('CONTAINER IMAGE UPLOAD FAILED LOGS BELOW:')
            self.logger.error(ex.output)
            self.logger.exception(ex)
            self.logger.error('END OF CONTAINER IMAGE UPLOAD FAILURE')


    def tag_qcow_images(promote_hash, promote_name):
        try:
            self.logger.info('Promoting the qcow image for dlrn hash %s on %s to %s',
                        full_hash, release, promote_name)
            command = 'bash'
            command.append(self.images_promote_script)
            command += ["-r", self.config.release]
            command += ["-p", promote_hash.full_hash]
            command += ["-l", promote_name]
            if self.config.dry_run:
                command.append(" --dry-run")
            output = subprocess.check_output(command, 
                                             stderr=subprocess.STDOUT)
            for line in output.split("\n"):
                self.logger.info(line)
        except subprocess.CalledProcessError as ex:
            self.logger.error('QCOW IMAGE UPLOAD FAILED LOGS BELOW:')
            self.logger.error(ex.output)
            self.logger.exception(ex)
            self.logger.error('END OF QCOW IMAGE UPLOAD FAILURE')

    def promote_single_link(self, candidate, target):
        self.logger.info('Trying to promote %s to %s', candidate, target)
        log_header = "%s->%s" % (candidate, target)
        self.logger.set_header(log_header)
            
        #candidate_hash = self.dlrnapi.fetch_hashes(candidate)
        candidate_hash = DlrnHash()
        candidate_hash.commit_hash = "c26e31248bee250c1792c67f463b77ac59d1aaf9"
        candidate_hash.distro_hash = "37239c88bdb32a4b89cd4dd81c7f1d8ab49dbbfa"

        if candidate_hash is None:
            raise PromotionSkip('Failed to fetch hashes for candidate')

        self.logger.info('candidate hash found: %s' % (str(candidate_hash)))
        log_header = "%s(%s)->%s" % (candidate, candidate_hash.short_hash, target)
        self.logger.set_header(log_header)

        target_current_hash = self.dlrnapi.fetch_hashes(target)
        if target_current_hash is None:
            self.logger.warning('Target has no current hash associated, no existing'
                           ' promotions or wrong target specified')
        else:
            self.logger.info('Target current hash found: %s' % str(target_current_hash))
#            if candidate_hash == target_current_hash:
#                raise PromotionSkip('candidate hash same as target')

        successful_jobs = self.dlrnapi.fetch_jobs(candidate_hash)
        successful_jobs_set = Set(successful_jobs.keys())
        required_jobs_set = Set(self.config.promotions[target]['jobs'])
        missing_jobs = list(required_jobs_set - successful_jobs_set)
        if missing_jobs:
            raise PromotionSkip('missing successful jobs: %s' % missing_jobs)
        # tagging containers goes first since it's the one that requires more
        # time.
        try:
            builder_job_url = successful_jobs[self.config.containers_builder]
            images_list_url = builder_job_url + "kolla/parsed_containers.txt"
            
        except KeyError:
            raise PromotionError("no containers builder job found")
        
        try:
            self.tag_containers(containter_hash, target, images_list_url)
        except:
            raise PromotionError
        try:
            self.dlrnapi.promote_link(api, new_hashes, promote_name)
            self.logger.info('SUCCESS promoting %s as %s (old: %s, new: %s)',
                        current_name, promote_name, old_hashes, new_hashes)
        except ApiException:
            raise PromotionError
        try:
            self.tag_qcow_images(new_hashes, promote_name)
        except:
            raise PromotionError
    
    def promote_all_links(self):
        '''Promote DLRN API links as a different one when all jobs are
        successful'''
        self.logger.info('STARTED promotion process with config %s', self.config.file_path)
        for target, definition in self.config.promotions.iteritems():
            candidate = definition['candidate']
            try:
                self.promote_single_link(candidate, target)
            except PromotionError as ex:
                self.logger.error("FAILED: %s" % ex.message)
            except PromotionSkip as ex:
                self.logger.warning("Skipping: %s" % ex.message)
            self.logger.unset_header()

        self.logger.info("FINISHED promotion process")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: %s <config-file>" % sys.argv[0])
    else:
        promoter = Promoter(sys.argv[1])
        promoter.promote_all_links()

