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

import urllib
from bs4 import BeautifulSoup

from dlrnapi_client.rest import ApiException
import dlrnapi_client

def get_full_hash(commit_hash, distro_hash):
    return "{}_{}".format(commit_hash, distro_hash[:8])


def get_last_successful_promotion_hash(dlrn, link, hashes):
    ''' Get the hash that was promoted '''
    logger =  logging.getLogger('TestPromoter')
    params = dlrn_client.PromotionQuery()

def get_tagged_image_hash():
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
        print("status passing")
    elif status == 'failed':
        # check string for failing hashes
        print("status failing")

# promoter Skipping promotion of {'timestamp': 1568520108, 'distro_hash': '06d9e873ed88e522740667d548e901f82cdcc6bb', 'promote_name': 'tripleo-ci-testing', 'user': 'review_rdoproject_org', 'repo_url': 'https://trunk.rdoproject.org/centos7-rocky/21/d1/21d1e74a7fda5b8954f25227eb04c716799a982c_06d9e873', 'full_hash': '21d1e74a7fda5b8954f25227eb04c716799a982c_06d9e873', 'repo_hash': '21d1e74a7fda5b8954f25227eb04c716799a982c_06d9e873', 'commit_hash': '21d1e74a7fda5b8954f25227eb04c716799a982c'}

#parse_promotion_logs('http://xx/centos7_rocky.log', '022baa43f6715d15c1f69f86ebb82697a1d852c7', 'd663cffd145bd27be4b125e005f9ca5072acf098', 'success')


