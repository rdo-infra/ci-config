#!/usr/bin/env python
"""
This script tests the steps of the promoter workflow.
 - Checks the dlrn API that the hash under test has been promoted to the promotion target
 - Checks that containers with that hash are pushed to repo 2
 - Checks that images are uploaded with that hash and linked to promotion target
 - Checks the promoter logs for expected strings

See https://github.com/rdo-infra/ci-config/blob/master/ci-scripts/dlrnapi_promoter/dlrnapi_promoter.py
"""

import datetime
import docker
import filecmp
import logging
import os
import pysftp
import re

import urllib
from bs4 import BeautifulSoup

from dlrnapi_client.rest import ApiException
import dlrnapi_client

def get_full_hash(commit_hash, distro_hash):
    return "{}_{}".format(commit_hash, distro_hash[:8])

def check_dlrn_promoted_hash(dlrn_host, promotion_target, commit_hash, distro_hash):
    ''' Check that the commit, distro hash has been promoted to
        promotion_target as recorded in DLRN. '''

    logger = logging.getLogger('TestPromoter')
    api_client = dlrnapi_client.ApiClient(host=dlrn_host)
    dlrn = dlrnapi_client.DefaultApi(api_client=api_client)
    params = dlrnapi_client.PromotionQuery()
    params.commit_hash = commit_hash
    params.distro_hash = distro_hash
    try:
        api_response = dlrn.api_promotions_get(params)
        logger.debug(api_response)
    except ApiException:
        logger.error('Exception when calling api_promotions_get: %s',
                     ApiException)
        raise
    try:
        assert any([(promotion.promote_name == promotion_target) for promotion in api_response])
    except AssertionError as e:
         print("Expected commit hash: " + commit_hash + " has not been promoted to." + promotion_target)
         raise e

def query_container_registry_promotion(registry, repo, tag):
    ''' Check that the hash containers have been pushed to the
        promotion registry with the promotion_target tag. '''

    docker_client = Client(base_url=registry)
    # docker_client = docker.from_env()
    # images_promoted = ci-scripts/dlrnapi_promoter/tests/staging-setup/samples/docker_images.txt
    #    try:
    #        source_image = docker_client.images.get(images_promoted)
    #    except docker.errors.ImageNotFound:
    #        registry_data = docker_client.images.get_registry_data(
    #            image_promoted)
    #       source_image = registry_data.pull(platform="x86_64")

def compare_tagged_image_hash(images_base_dir, user, key_path, distro, release, promotion_target, commit_hash, distro_hash):
    ''' Ensure that the promotion target images directory
        is a soft link to the promoted full hash images directory. '''

    logger = logging.getLogger('TestPromoter')
    full_hash = get_full_hash(commit_hash, distro_hash)

    if 'promoter-staging' not in images_base_dir:
        with pysftp.Connection(host=images_base_dir, username=user, private_key=key_path) as sftp:
            try:
                images_dir = os.path.join('/var/www/html/images', release, 'rdo_trunk')
                assert os.path.join(images_dir, full_hash) == sftp.readlink(
                    os.path.join(images_dir, promotion_target))
            except AssertionError as e:
                print("Promotion target dir is not a softlink of the full hash dir.")
                raise e
    else:
        # Check that the promotion_target dir is a soft link
        try:
            images_dir = os.path.join(images_base_dir,
                'overcloud_images',
                distro,
                release,
                'rdo_trunk')
            assert os.path.join(images_dir, full_hash) == os.readlink(os.path.join(images_dir, promotion_target))
        except AssertionError as e:
            print("Promotion target dir is not a softlink of the full hash dir.")
            raise e

def parse_promotion_logs(logfile, release, promotion_target, commit_hash, distro_hash, status):
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

    if status == 'success':
        # Check strings for passing hashes
        print("Status Passing:")
        # Build pattern for successful promotion
        success_pattern_container = re.compile(r'promoter Promoting the container images for dlrn hash ' + re.escape(commit_hash))
        success_pattern_images = re.compile(r'Promoting the qcow image for dlrn hash ' + re.escape(full_hash) + r' on ' + re.escape(release) + r' to ' + re.escape(promotion_target))
        success_pattern = re.compile(r'promoter Successful jobs for {\'timestamp\': (\d+), \'distro_hash\': \''  + re.escape(distro_hash) + r'\', (.*) \'full_hash\': \'' + re.escape(full_hash) + r'\', \'repo_hash\': \'' + re.escape(full_hash) + r'\', \'commit_hash\': \'' + re.escape(commit_hash) + r'\'}')

        for pattern in [success_pattern, success_pattern_images, success_pattern_container]:
            try:
                success_pattern_search = pattern.search( logfile_contents )
                assert success_pattern_search.group()
            except AttributeError as e:
                print("Success text pattern not found - ", pattern)
                raise e

    elif status == 'failed':
        # Check string for failing hashes
        print("Status Failing:")
        # Build pattern for failing promotion
        fail_pattern = re.compile(r'promoter Skipping promotion of {\'timestamp\': (\d+), \'distro_hash\': \''  + re.escape(distro_hash) + r'\', (.*) \'full_hash\': \'' + re.escape(full_hash) + r'\', \'repo_hash\': \'' + re.escape(full_hash) + r'\', \'commit_hash\': \'' + re.escape(commit_hash) + r'\'}')
        try:
            fail_pattern_search = fail_pattern.search( logfile_contents )
            assert fail_pattern_search.group()
        except AttributeError as e:
            print("Fail text pattern not found - ", fail_pattern)
            raise e

def main():

    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger("TestPromoter")
    log.setLevel(logging.DEBUG)

if __name__ == "__main__":
    main()
