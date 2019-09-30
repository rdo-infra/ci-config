#!/usr/bin/env python
"""
This script tests the steps of the promoter workflow.
 - Checks the dlrn API that the hash under test has been promoted
   to the promotion target
 - Checks that containers with that hash are pushed to repo 2
 - Checks that images are uploaded with that hash and linked to
   promotion target
 - Checks the promoter logs for expected strings

"""

import argparse
import dlrnapi_client
import docker
import logging
import os
import re
import urllib
import yaml


def get_full_hash(commit_hash, distro_hash):
    return "{}_{}".format(commit_hash, distro_hash[:8])


def check_dlrn_promoted_hash(dlrn_host, promotion_target,
                             commit_hash, distro_hash):
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
    except dlrnapi_client.rest.ApiException:
        logger.error('Exception when calling api_promotions_get: %s',
                     dlrnapi_client.rest.ApiException)
        raise

    error_message = ("Expected commit hash: {}"
                     " has not been promoted to {}."
                     "".format(commit_hash, promotion_target))
    conditions = [(promotion.promote_name == promotion_target)
                  for promotion in api_response]
    assert any(conditions), error_message


def query_container_registry_promotion(registry_rdo, registry_docker_io,
                                       promotion_target, commit_hash,
                                       distro_hash):
    ''' Check that the hash containers have been pushed to the
        promotion registry with the promotion_target tag. '''

    # logger = logging.getLogger('TestPromoter')
    full_hash = get_full_hash(commit_hash, distro_hash)
    docker_client = docker.DockerClient(base_url=registry_docker_io)
    # docker_client = docker.from_env()
    if 'localhost' in registry_rdo:
        base_path = os.path.dirname(os.path.abspath(__file__))
        images_path = os.path.join(base_path,
                                   'samples/docker_images.txt')
        with open(images_path) as images_promoted:
            lines = images_promoted.read_lines()

        for line in lines:
            if full_hash in line:
                try:
                    line = line.replace(
                        registry_rdo, registry_docker_io)
                    docker_client.images.get(line)
                except docker.errors.ImageNotFound:
                    docker_client.images.get_registry_data(
                        line)
                    line = line.replace(full_hash, promotion_target)
                    docker_client.images.get(line)
                except docker.errors.ImageNotFound:
                    docker_client.images.get_registry_data(
                        line)
    else:
        # TODO: how to verify promoter containers
        print("Compare images tagged with hash and promotion target:")


def compare_tagged_image_hash(images_base_dir, user, key_path,
                              distro, release, promotion_target,
                              commit_hash, distro_hash):
    ''' Ensure that the promotion target images directory
        is a soft link to the promoted full hash images directory. '''

    # logger = logging.getLogger('TestPromoter')
    full_hash = get_full_hash(commit_hash, distro_hash)

    if 'promoter-staging' not in images_base_dir:
        print("Install required for nonstaging env")
        import pysftp
        sftp = pysftp.Connection(
            host=images_base_dir,
            username=user, private_key=key_path)

        images_dir = os.path.join(
            '/var/www/html/images',
            release, 'rdo_trunk')
        hash_path = os.path.join(images_dir, full_hash)
        rl_module = sftp
    else:
        # Check that the promotion_target dir is a soft link
        images_dir = os.path.join(
            images_base_dir, 'overcloud_images',
            distro, release, 'rdo_trunk')
        rl_module = os

    error_message = "Promotion target dir is not a softlink"
    hash_path = os.path.join(images_dir, full_hash)
    promoted_hash_path = rl_module.readlink(
        os.path.join(images_dir, promotion_target))

    assert hash_path == promoted_hash_path, error_message


def parse_promotion_logs(logfile, release, promotion_target,
                         commit_hash, distro_hash, status):
    ''' Check that the promotion logs have the right
        strings printed for the promotion status '''

    logger = logging.getLogger('TestPromoter')
    logger.debug("Open promoter file for reading")

    full_hash = get_full_hash(commit_hash, distro_hash)
    # Check if the logfile passed is web hosted
    if 'http' in logfile:
        from bs4 import BeautifulSoup
        logger.debug("Reading web hosted log file")
        url = urllib.request.urlopen(logfile).read()
        soup = BeautifulSoup(url, 'html.parser')
        logfile_contents = soup.get_text()
    else:
        logger.debug("Reading local log file")
        with open(logfile, 'r') as lf:
            logfile_contents = lf.read()

    # Check that the promoter process finished
    error_message = "Promoter never finished"
    assert 'promoter FINISHED' in logfile_contents, error_message

    if status == 'success':
        # Check strings for passing hashes
        print("Status Passing:")
        # Build pattern for successful promotion
        success_pattern_container = re.compile(
            r'promoter Promoting the container images for dlrn hash '
            + re.escape(commit_hash))
        success_pattern_images = re.compile(
            r'Promoting the qcow image for dlrn hash '
            + re.escape(full_hash) + r' on '
            + re.escape(release) + r' to '
            + re.escape(promotion_target))
        success_pattern = re.compile(
            r'Successful jobs for {\'timestamp\': (\d+), \'distro_hash\': \''
            + re.escape(distro_hash)
            + r'\', (.*) \'full_hash\': \''
            + re.escape(full_hash)
            + r'\', \'repo_hash\': \''
            + re.escape(full_hash) + r'\', \'commit_hash\': \''
            + re.escape(commit_hash) + r'\'}')

        success_patterns = [
            success_pattern,
            success_pattern_images,
            success_pattern_container
        ]
        for pattern in success_patterns:
            success_pattern_search = pattern.search(logfile_contents)
            error_message = "Success text pattern not found - %s" % pattern
            assert success_pattern_search.group(), error_message

    elif status == 'failed':
        # Check string for failing hashes
        print("Status Failing:")
        # Build pattern for failing promotion
        fail_pattern = re.compile(
            r'promoter Skipping promotion of '
            + r'{\'timestamp\': (\d+), \'distro_hash\': \''
            + re.escape(distro_hash) + r'\', (.*) \'full_hash\': \''
            + re.escape(full_hash)
            + r'\', \'repo_hash\': \''
            + re.escape(full_hash) + r'\', \'commit_hash\': \''
            + re.escape(commit_hash) + r'\'}')
        error_message("Fail text pattern not found - %s" % fail_pattern)
        fail_pattern_search = fail_pattern.search(logfile_contents)
        assert fail_pattern_search.group(), error_message


def main():

    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger("TestPromoter")
    log.setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser(
        description='Pass a config file.')
    parser.add_argument('--config_file', dest='config_file')
    args = parser.parse_args()

    test_config_file = args.config_file
    with open(test_config_file) as tcf:
        test_config = yaml.safe_load(tcf)

    check_dlrn_promoted_hash(
        test_config['dlrn_host'],
        test_config['promotion_target'],
        test_config['commit_hash'], test_config['distro_hash'])
    query_container_registry_promotion(
        test_config['registry_rdo'],
        test_config['registry_docker_io'],
        test_config['promotion_target'],
        test_config['commit_hash'],
        test_config['distro_hash'])
    compare_tagged_image_hash(
        test_config['images_base_dir'],
        test_config['user'],
        test_config['key_path'],
        test_config['distro'],
        test_config['release'],
        test_config['promotion_target'],
        test_config['commit_hash'],
        test_config['distro_hash'])
    parse_promotion_logs(
        test_config['logfile'],
        test_config['release'],
        test_config['promotion_target'],
        test_config['commit_hash'],
        test_config['distro_hash'],
        test_config['status'])


if __name__ == "__main__":
    main()
