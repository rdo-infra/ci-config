#!/usr/bin/env python

from __future__ import print_function
from datetime import datetime
from sets import Set
import ConfigParser
import logging
import os
import sys

from dlrnapi_client.rest import ApiException
import dlrnapi_client

def fetch_hashes(dlrn, link):
    '''Get the commit and distro hashes for a specific promotion link'''
    params = dlrnapi_client.PromotionQuery()
    params.promote_name = link
    try:
        api_response = dlrn.api_promotions_get(params)
    except ApiException:
        logging.error('Exception when calling api_promotions_get: %s',
                      ApiException)
        return None
    try:
        return {'commit_hash': api_response[0].commit_hash,
                'distro_hash': api_response[0].distro_hash}
    except IndexError:
        return None

def fetch_jobs(dlrn, hash_values):
    '''Fetch the successfully finished jobs for a specific DLRN hash'''
    params = dlrnapi_client.Params2()
    params.commit_hash = hash_values['commit_hash']
    params.distro_hash = hash_values['distro_hash']
    params.success = str(True)

    try:
        api_response = dlrn.api_repo_status_get(params)
    except ApiException:
        logging.error('Exception when calling api_repo_status_get: %s',
                      ApiException)
        return None
    logging.debug('Successful jobs for %s:', hash_values)
    for result in api_response:
        logging.debug('%s at %s, logs at %s', result.job_id,
                      datetime.fromtimestamp(result.timestamp).isoformat(),
                      result.url)
    return [details.job_id for details in api_response]

def promote_link(dlrn, hash_values, link):
    '''Promotes a set of hash values as a named link using DLRN API'''
    params = dlrnapi_client.Promotion()
    params.commit_hash = hash_values['commit_hash']
    params.distro_hash = hash_values['distro_hash']
    params.promote_name = link
    try:
        dlrn.api_promote_post(params)
        return True
    except ApiException:
        logging.error('Exception when calling api_promote_post: %s',
                      ApiException)
        return False

def promote_all_links(config_file):
    '''Promote DLRN API links as a different one when all jobs are
    successful'''
    config = ConfigParser.SafeConfigParser(allow_no_value=True)
    config.read(config_file)

    # setup the API connection
    dry_run = config.getboolean('main', 'dry_run')
    api_client = dlrnapi_client.ApiClient(host=config.get('main', 'api_url'))
    dlrnapi_client.configuration.username = config.get('main', 'username')
    dlrnapi_client.configuration.password = os.getenv('DLRNAPI_PASSWORD', None)
    api_instance = dlrnapi_client.DefaultApi(api_client=api_client)
    config.remove_section('main')
    logging.info('Using API URL: %s', api_client.host)

    # load the promote_from data
    promote_from = {k: v for k, v in config.items('promote_from')}
    logging.debug('Attempting to promote these DLRN links: %s',
                  promote_from)
    config.remove_section('promote_from')

    # load the promotion requirements
    job_reqs = {}
    sections = config.sections()
    for section in sections:
        job_reqs[section] = [k for k, v in config.items(section)]
    logging.debug('Promotion requirements loaded: %s', job_reqs)

    for promote_name, current_name in promote_from.items():
        logging.info('Trying to promote %s to %s', current_name, promote_name)
        old_hashes = fetch_hashes(api_instance, promote_name)
        new_hashes = fetch_hashes(api_instance, current_name)
        if new_hashes is None:
            logging.error('Failed to fetch hashes for %s, skipping promotion',
                          current_name)
            continue
        if old_hashes is None:
            logging.warning('Failed to fetch hashes for %s, no previous '
                            'promotion or typo in the link name',
                            promote_name)
        if new_hashes == old_hashes:
            logging.info('Same hashes for %s and %s %s, skipping promotion',
                         current_name, promote_name, old_hashes)
            continue
        successful_jobs = Set(fetch_jobs(api_instance, new_hashes))
        required_jobs = Set(job_reqs[promote_name])
        missing_jobs = list(required_jobs - successful_jobs)
        if missing_jobs:
            logging.info('Skipping promotion of %s to %s, missing successful '
                         'jobs: %s',
                         current_name, promote_name, missing_jobs)
            continue
        if dry_run:
            logging.info('DRY RUN: promotion conditions satisfied, '
                         'skipping promotion of %s to %s (old: %s, new: %s)',
                         current_name, promote_name, old_hashes, new_hashes)
        else:
            promote_link(api_instance, hashes, promote_from[promote_name])
            logging.info('Promoting %s as %s (old: %s, new: %s)',
                         current_name, promote_name, old_hashes, new_hashes)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    if len(sys.argv) < 2:
        print("Usage: %s <config-file>" % sys.argv[0])
    else:
        promote_all_links(sys.argv[1])
