#!/usr/bin/env python
"""
This script tests the steps of the promoter workflow.
 - Checks the dlrn API that the hash under test has been promoted to the promotion target
 - Checks that containers with that hash are pushed to repo 2
 - Checks that images are uploaded with that hash and linked to promotion target
 - Checks the promoter logs for expected strings

See https://github.com/rdo-infra/ci-config/blob/master/ci-scripts/dlrnapi_promoter/dlrnapi_promoter.py
"""

import argparse
import docker
import filecmp
import logging
import os
#import pysftp
import re

import urllib
from bs4 import BeautifulSoup

from dlrnapi_client.rest import ApiException
import dlrnapi_client

from staging_environment import get_full_hash

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
         print("Expected commit hash: " + commit_hash +
               " has not been promoted to." + promotion_target)
         raise e

def query_container_registry_promotion(registry_rdo, registry_docker_io, promotion_target, commit_hash, distro_hash):
    ''' Check that the hash containers have been pushed to the
        promotion registry with the promotion_target tag. '''

    logger = logging.getLogger('TestPromoter')
    full_hash = get_full_hash(commit_hash, distro_hash)
    docker_client = docker.DockerClient(base_url=registry_docker_io)
    # docker_client = docker.from_env()
    if 'localhost' in registry_rdo:
        base_path = os.path.dirname(os.path.abspath(__file__))
        images_promoted = open(os.path.join(base_path, 'samples/docker_images.txt'), 'r')
        lines = images_promoted.readline()
        for line in lines:
            try:
                line = line.replace(registry_rdo, registry_docker_io)
                source_image = docker_client.images.get(line)
            except docker.errors.ImageNotFound:
                registry_data = docker_client.images.get_registry_data(
                    line)
                line = line.replace(full_hash, promotion_target)
                source_image = docker_client.images.get(line)
            except docker.errors.ImageNotFound:
                registry_data = docker_client.images.get_registry_data(
                    line)
    else:
        # TODO: how to verify promoter containers
        print("Compare images tagged with hash and those tagged promlotion target:")

def compare_tagged_image_hash(images_base_dir, user, key_path,
                              distro, release, promotion_target, commit_hash, distro_hash):
    ''' Ensure that the promotion target images directory
        is a soft link to the promoted full hash images directory. '''

    logger = logging.getLogger('TestPromoter')
    full_hash = get_full_hash(commit_hash, distro_hash)

    if 'promoter-staging' not in images_base_dir:
        #with pysftp.Connection(host=images_base_dir, username=user, private_key=key_path) as sftp:
        #    try:
        #        images_dir = os.path.join('/var/www/html/images', release, 'rdo_trunk')
        #        assert os.path.join(images_dir, full_hash) == sftp.readlink(
        #            os.path.join(images_dir, promotion_target))
        #    except AssertionError as e:
        #        print("Promotion target dir is not a softlink of the full hash dir.")
        #        raise e
    else:
        # Check that the promotion_target dir is a soft link
        try:
            images_dir = os.path.join(images_base_dir,
                'overcloud_images',
                distro,
                release,
                'rdo_trunk')
            assert os.path.join(images_dir, full_hash) == os.readlink(
                   os.path.join(images_dir, promotion_target))
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

    base_path = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description='Pass a config file.')
    parser.add_argument('--config_file', dest='config_file')

    test_config_file = os.path.join(base_path, args.config_file)
    tcf = open(test_config_file)
    test_config = yaml.safe_load(tcf)

    check_dlrn_promoted_hash(test_config['dlrn_host'], test_config['promotion_target'],
                             test_config['commit_hash'], test_config['distro_hash'])
    query_container_registry_promotion(test_config['registry_rdo'], test_config['registry_docker_io'],
                                       test_config['promotion_target'], test_config['commit_hash'],
                                       test_config['distro_hash'])
    compare_tagged_image_hash(test_config['images_base_dir'], test_config['user'], test_config['key_path'],
                              test_config['distro'], test_config['release'], test_config['promotion_target'],
                              test_config['commit_hash'], test_config['distro_hash'])
    parse_promotion_logs(test_config['logfile'], test_config['release'], test_config['promotion_target'],
                         test_config['commit_hash'], test_config['distro_hash'], test_config['status'])

if __name__ == "__main__":
    main()
