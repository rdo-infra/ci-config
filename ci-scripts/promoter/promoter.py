#!/usr/bin/env python

from __future__ import print_function
from sets import Set
import ConfigParser
import logging
import os
import sys
import urllib2

from dlrnapi_client.rest import ApiException
import dlrnapi_client
import yaml

def fetch_hashes(url, link):
    '''Get the commit and distro hashes from commit.yaml

    The commit.yaml is a file DLRN puts in the repo directory and it contains
    the untruncated hashes. This function should be reworked when DLRN API
    supports the query of promotion links by the /api/promotions-get call'''

    commit_url = '/'.join([url, link, 'commit.yaml'])
    try:
        commit_yaml = yaml.load(urllib2.urlopen(commit_url).read())
    except urllib2.HTTPError:
        logging.warning('Exception while downloading %s', commit_url)
        return None
    hash_values = {k: v for k, v in commit_yaml['commits'][0].items() if k in
                   ['commit_hash', 'distro_hash']}
    return hash_values

def fetch_jobs(dlrn, hash_values):
    '''Fetch the successfully finished jobs for a specific DLRN hash'''
    params = dlrnapi_client.Params2()
    params.commit_hash = hash_values['commit_hash']
    params.distro_hash = hash_values['distro_hash']
    params.success = str(True)

    try:
        api_response = dlrn.api_repo_status_get(params)
    except ApiException:
        logging.error('Exception when calling api_repo_status_get %s',
                      ApiException)
        return None
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
        logging.error('Exception when calling api_promote_post %s:',
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

    # until /api/promotions will start working we need this
    dlrn_base_url = config.get('main', 'dlrn_base_url')

    config.remove_section('main')
    logging.info('Using API URL: %s', api_client.host)

    # load the from-to targets
    targets = {k: v for k, v in config.items('promote_from_to')}
    logging.debug('Attempting to promote from/to these DLRN links: %s',
                  targets)
    config.remove_section('promote_from_to')

    # load the promotion requirements
    job_reqs = {}
    sections = config.sections()
    for section in sections:
        job_reqs[section] = [k for k, v in config.items(section)]
    logging.debug('Promotion requirements loaded: %s', job_reqs)

    for link_name in targets.keys():
        old_hashes = fetch_hashes(dlrn_base_url, targets[link_name])
        new_hashes = fetch_hashes(dlrn_base_url, link_name)
        if new_hashes is None:
            logging.error('Failed to fetch hashes for %s, skipping promotion',
                          link_name)
            continue
        if old_hashes is None:
            logging.warning('Failed to fetch hashes for %s, no previous '
                            'promotion or typo in the link name',
                            targets[link_name])
        successful_jobs = Set(fetch_jobs(api_instance, new_hashes))
        logging.debug('Successful jobs for link %s %s: %s',
                      link_name, new_hashes, list(successful_jobs))
        required_jobs = Set(job_reqs[link_name])
        missing_jobs = list(required_jobs - successful_jobs)
        if missing_jobs:
            logging.info('Skipping promotion of %s to %s, missing successful '
                         'jobs: %s',
                         link_name, targets[link_name], missing_jobs)
            continue
        if dry_run:
            logging.info('DRY RUN: promotion conditions satisfied, '
                         'skipping promotion of %s to %s (old: %s, new: %s)',
                         link_name, targets[link_name], old_hashes, new_hashes)
        else:
            #promote_link(api_instance, hashes, targets[link_name])
            logging.info('Promoting %s as %s (old: %s, new: %s)', link_name,
                         targets[link_name], old_hashes, new_hashes)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    if len(sys.argv) < 2:
        print("Usage: %s <config-file>" % sys.argv[0])
    else:
        promote_all_links(sys.argv[1])
