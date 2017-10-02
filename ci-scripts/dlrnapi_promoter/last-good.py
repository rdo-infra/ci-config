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


def fetch_all_hashes(dlrn, link):
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
        return api_response
    except IndexError:
        return None


def setup_logging(log_file):
    '''Setup logging for the script'''
    logger = logging.getLogger('promoter')
    #logger.setLevel(logging.DEBUG)
    logger.setLevel(logging.INFO)
    #log_handler = logging.handlers.TimedRotatingFileHandler(
    #    os.path.expanduser(log_file), when='d', interval=1, backupCount=7)
    log_handler = logging.StreamHandler()
    log_formatter = logging.Formatter('%(asctime)s %(process)d '
                                      '%(levelname)-8s %(name)s %(message)s')
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)


def promote_all_links(api, promote_from, job_reqs, dry_run, release):
    '''Promote DLRN API links as a different one when all jobs are
    successful'''
    logger = logging.getLogger('promoter')

    for promote_name, current_name in promote_from.items():
        hashes = fetch_all_hashes(api, current_name)
        if hashes is None:
            logger.error('Failed to fetch hashes for %s, skipping promotion',
                         current_name)
            continue
        for current_result in hashes:
            new_hashes = {'commit_hash': current_result.commit_hash,
                          'distro_hash': current_result.distro_hash}
            logger.info('Evaluating results for previous %s link (to be '
                        'promoted as %s) (%s), promoted at %s',
                        current_name, promote_name, new_hashes,
                        datetime.fromtimestamp(current_result.timestamp).isoformat())
            successful_jobs = Set(fetch_jobs(api, new_hashes))
            required_jobs = Set(job_reqs[promote_name])
            missing_jobs = list(required_jobs - successful_jobs)
            if missing_jobs:
                logger.info('Missing successful '
                            'jobs: %s',
                            missing_jobs)
                continue
            if dry_run:
                logger.info('Good hash found. See the previous long line for details.')
                break


def promoter(config_file):
    config = ConfigParser.SafeConfigParser(allow_no_value=True)
    config.read(config_file)

    setup_logging(config.get('main', 'log_file'))
    logger = logging.getLogger('promoter')

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
