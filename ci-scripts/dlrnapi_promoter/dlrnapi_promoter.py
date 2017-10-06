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


def fetch_hashes(dlrn, link):
    '''Get the commit and distro hashes for a specific promotion link'''
    logger = logging.getLogger('promoter')
    params = dlrnapi_client.PromotionQuery()
    params.promote_name = link
    try:
        api_response = dlrn.api_promotions_get(params)
    except ApiException:
        logger.error('Exception when calling api_promotions_get: %s',
                     ApiException)
        return None
    try:
        return {'commit_hash': api_response[0].commit_hash,
                'distro_hash': api_response[0].distro_hash}
    except IndexError:
        return None


def fetch_jobs(dlrn, hash_values):
    '''Fetch the successfully finished jobs for a specific DLRN hash'''
    logger = logging.getLogger('promoter')
    params = dlrnapi_client.Params2()
    params.commit_hash = hash_values['commit_hash']
    params.distro_hash = hash_values['distro_hash']
    params.success = str(True)

    try:
        api_response = dlrn.api_repo_status_get(params)
    except ApiException:
        logger.error('Exception when calling api_repo_status_get: %s',
                     ApiException)
        return None
    logger.debug('Successful jobs for %s:', hash_values)
    for result in api_response:
        logger.debug('%s at %s, logs at %s', result.job_id,
                     datetime.fromtimestamp(result.timestamp).isoformat(),
                     result.url)
    return [details.job_id for details in api_response]


def promote_link(dlrn, hash_values, link):
    '''Promotes a set of hash values as a named link using DLRN API'''
    logger = logging.getLogger('promoter')
    params = dlrnapi_client.Promotion()
    params.commit_hash = hash_values['commit_hash']
    params.distro_hash = hash_values['distro_hash']
    params.promote_name = link
    try:
        dlrn.api_promote_post(params)
        return True
    except ApiException:
        logger.error('Exception when calling api_promote_post: %s',
                     ApiException)
        return False


def setup_logging(log_file):
    '''Setup logging for the script'''
    logger = logging.getLogger('promoter')
    logger.setLevel(logging.DEBUG)
    log_handler = logging.handlers.TimedRotatingFileHandler(
        os.path.expanduser(log_file), when='d', interval=1, backupCount=7)
    log_formatter = logging.Formatter('%(asctime)s %(process)d '
                                      '%(levelname)-8s %(name)s %(message)s')
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)


def tag_containers(new_hashes, release, promote_name):
    logger = logging.getLogger('promoter')
    env = os.environ
    relpath = "ci-scripts/dlrnapi_promoter"
    script_root = os.path.abspath(sys.path[0]).replace(relpath,"")
    env['RELEASE'] = release
    env['COMMIT_HASH'] = new_hashes['commit_hash']
    env['DISTRO_HASH'] = new_hashes['distro_hash']
    env['FULL_HASH'] = new_hashes['full_hash']
    env['PROMOTE_NAME'] = promote_name
    env['SCRIPT_ROOT'] = script_root
    promote_playbook = (
        script_root + 'ci-scripts/container-push/container-push.yml'
    )
    commit_hash = new_hashes['commit_hash']
    try:
        logger.info('Promoting the container images for dlrn hash %s on '
                    '%s to %s', commit_hash, release, promote_name)
        container_logs = subprocess.check_output(
                         ['ansible-playbook', promote_playbook],
                         env=env, stderr=subprocess.STDOUT).split("\n")
        for line in container_logs:
            logger.info(line)
    except subprocess.CalledProcessError as ex:
        logger.error('CONTAINER IMAGE UPLOAD FAILED LOGS BELOW:')
        logger.error(ex.output)
        logger.exception(ex)
        logger.error('END OF CONTAINER IMAGE UPLOAD FAILURE')


def tag_qcow_images(new_hashes, release, promote_name):
    logger = logging.getLogger('promoter')
    relpath = "ci-scripts/dlrnapi_promoter"
    script_root = os.path.abspath(sys.path[0]).replace(relpath,"")
    promote_script = script_root + 'ci-scripts/promote-images.sh'
    full_hash = new_hashes['full_hash']
    try:
        logger.info('Promoting the qcow image for dlrn hash %s on %s to %s',
                    full_hash, release, promote_name)
        qcow_logs = subprocess.check_output(['bash', promote_script,
                                            release, full_hash,
                                            promote_name],
                                            stderr=subprocess.STDOUT
                                            ).split("\n")
        for line in qcow_logs:
            logger.info(line)
    except subprocess.CalledProcessError as ex:
        logger.error('QCOW IMAGE UPLOAD FAILED LOGS BELOW:')
        logger.error(ex.output)
        logger.exception(ex)
        logger.error('END OF QCOW IMAGE UPLOAD FAILURE')


def promote_all_links(api, promote_from, job_reqs, dry_run, release):
    '''Promote DLRN API links as a different one when all jobs are
    successful'''
    logger = logging.getLogger('promoter')

    for promote_name, current_name in promote_from.items():
        logger.info('Trying to promote %s to %s', current_name, promote_name)
        old_hashes = fetch_hashes(api, promote_name)
        new_hashes = fetch_hashes(api, current_name)
        logger.info('new hash found for %s: %s', str(new_hashes), current_name)
        full_new_hash='{0}_{1}'.format(new_hashes['commit_hash'],
                                       new_hashes['distro_hash'][:8])
        if new_hashes is None:
            logger.error('Failed to fetch hashes for %s, skipping promotion',
                         current_name)
            continue
        new_hashes['full_hash'] = full_new_hash
        if old_hashes is None:
            logger.warning('Failed to fetch hashes for %s, no previous '
                           'promotion or typo in the link name',
                           promote_name)
        if new_hashes == old_hashes:
            logger.info('Same hashes for %s and %s %s, skipping promotion',
                        current_name, promote_name, old_hashes)
            continue
        successful_jobs = Set(fetch_jobs(api, new_hashes))
        required_jobs = Set(job_reqs[promote_name])
        missing_jobs = list(required_jobs - successful_jobs)
        if missing_jobs:
            logger.info('Skipping promotion of %s to %s, missing successful '
                        'jobs: %s',
                        current_name, promote_name, missing_jobs)
            continue
        if dry_run:
            logger.info('DRY RUN: promotion conditions satisfied, '
                        'skipping promotion of %s to %s (old: %s, new: %s)',
                        current_name, promote_name, old_hashes, new_hashes)
        else:
            if promote_link(api, new_hashes, promote_name):
                logger.info('SUCCESS promoting %s as %s (old: %s, new: %s)',
                            current_name, promote_name, old_hashes, new_hashes)
                tag_containers(new_hashes, release, promote_name)
                tag_qcow_images(new_hashes, release, promote_name)
            else:
                logger.info('FAILED promoting %s as %s (old: %s, new: %s)',
                            current_name, promote_name, old_hashes, new_hashes)


def promoter(config_file):
    config = ConfigParser.SafeConfigParser(allow_no_value=True)
    config.read(config_file)

    setup_logging(config.get('main', 'log_file'))
    logger = logging.getLogger('promoter')

    logger.info('STARTED promotion process with config %s', config_file)

    try:
        git_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                           cwd=os.path.abspath(sys.path[0]))
        logger.info('Current git hash of repo containing the promoter '
                    'script: %s', git_hash.strip())
    except OSError:
        logger.debug('Failed to get the current git repo hash, check if '
                     'git is installed.')
    except subprocess.CalledProcessError:
        logger.debug('Failed to get the current git repo hash, probably not '
                     'running inside a git repository.')

    # setup the API connection
    dry_run = config.getboolean('main', 'dry_run')
    api_client = dlrnapi_client.ApiClient(host=config.get('main', 'api_url'))
    dlrnapi_client.configuration.username = config.get('main', 'username')
    if os.getenv('DLRNAPI_PASSWORD', None) is None:
        logger.warning('DLRNAPI_PASSWORD env variable is missing or empty, '
                       'promotion attempt will fail!')
    dlrnapi_client.configuration.password = os.getenv('DLRNAPI_PASSWORD', None)
    api_instance = dlrnapi_client.DefaultApi(api_client=api_client)
    release = config.get('main', 'release')
    config.remove_section('main')
    logger.info('Using API URL: %s', api_client.host)

    # load the promote_from data
    promote_from = {k: v for k, v in config.items('promote_from')}
    logger.debug('Attempting to promote these DLRN links: %s',
                 promote_from)
    config.remove_section('promote_from')

    # load the promotion requirements
    job_reqs = {}
    sections = config.sections()
    for section in sections:
        job_reqs[section] = [k for k, v in config.items(section)]
    logger.debug('Promotion requirements loaded: %s', job_reqs)

    promote_all_links(api_instance, promote_from, job_reqs, dry_run, release)
    logger.info("FINISHED promotion process")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: %s <config-file>" % sys.argv[0])
    else:
        promoter(sys.argv[1])
