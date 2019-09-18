#!/usr/bin/env python
"""
This script tests the steps of the promoter workflow.
 - Checks the dlrn API for the hash under test
 - Checks that containers tagged with that hash are pushed to
repo 1
 - Checks that images are uploaded with that hash
 - Checks that containers with that hash are pushed to repo 2
 - Checks the promoter logs for expected strings

See https://github.com/rdo-infra/ci-config/blob/master/ci-scripts/dlrnapi_promoter/dlrnapi_promoter.py
"""

import datetime
import docker
import logging
import os
import re

import urllib
from bs4 import BeautifulSoup

from dlrnapi_client.rest import ApiException
import dlrnapi_client

def get_full_hash(commit_hash, distro_hash):
    return "{}_{}".format(commit_hash, distro_hash[:8])


def query_container_registry_promotion(registry, repo, tag):
    ''' Check that the containers have been pushed to the
        promotion registry'''

    # Depends on the type of registry - v1 vs. v2


def get_tagged_image_hash(image_server, release_dir, promotion_target):
    ''' Get the hash of the image tagged with promotion name '''


def parse_promotion_logs(logfile, commit_hash, distro_hash, status):
    ''' Check that the promotion logs have the right
        strings printed for the promotion status '''

    logger = logging.getLogger('TestPromoter')
    logger.debug("Open promoter file for reading")

    full_hash = get_full_hash(commit_hash, distro_hash)
    # Check if the logfile passed is web hosted
    if 'http' in logfile:
        logger.debug("Reading web hosted log file")
        url = urllib.request.urlopen(logfile).read()
        soup = BeautifulSoup(url, 'html.parser')
        logfile_contents = soup.get_text()
    else:
        logger.debug("Reading local log file")
        logfile_contents = open(logfile, 'r').read()

    # Check that the promoter process finished
    try:
        assert 'promoter FINISHED promotion process' in logfile_contents
    except AssertionError as e:
         print("Promoter never finished")
         raise e

    # Check for strings expected for the status passed
    if status == 'success':
        # check strings for passing hashes
        print("Status Passing:")
        # Build pattern for successful promotion
        success_pattern_container = re.compile(r'promoter Promoting the container images for dlrn hash ' + re.escape(commit_hash))
        success_pattern = re.compile(r'promoter Successful jobs for {\'timestamp\': (\d+), \'distro_hash\': \''  + re.escape(distro_hash) + r'\', (.*) \'full_hash\': \'' + re.escape(full_hash) + r'\', \'repo_hash\': \'' + re.escape(full_hash) + r'\', \'commit_hash\': \'' + re.escape(commit_hash) + r'\'}')
        success_pattern_search = success_pattern.search( logfile_contents )
        print(success_pattern_search.group())
        success_pattern_container_search = success_pattern_container.search( logfile_contents )
        print(success_pattern_container_search.group())
    elif status == 'failed':
        # check string for failing hashes
        print("Status Failing:")
        # Build pattern for failing promotion
        fail_pattern = re.compile(r'promoter Skipping promotion of {\'timestamp\': (\d+), \'distro_hash\': \''  + re.escape(distro_hash) + r'\', (.*) \'full_hash\': \'' + re.escape(full_hash) + r'\', \'repo_hash\': \'' + re.escape(full_hash) + r'\', \'commit_hash\': \'' + re.escape(commit_hash) + r'\'}')
        fail_pattern_search = fail_pattern.search( logfile_contents )
        print(fail_pattern_search.group())


#parse_promotion_logs('http://xx/centos7_rocky.log', '214ee82e455ebad5aa41dd3599cd82576bbdb9dc', '798f6b1aca244c3dd2ab5634f0a8947b2c3c8ffc', 'failed')
#parse_promotion_logs('http://xx/centos7_master.log-20190914', '4e2116ddc27bd6f381721f058f47322245141a39', 'bbaf1d8e7dd70fd6caf6ce80315e9f48b522ad97', 'success')


