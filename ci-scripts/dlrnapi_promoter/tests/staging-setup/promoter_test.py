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
try:
    import urllib2 as url_lib
except ImportError:
    import urllib.request as url_lib
import yaml


def get_full_hash(commit_hash, distro_hash):
    return "{}_{}".format(commit_hash, distro_hash[:8])


def check_dlrn_promoted_hash(stage_info):
    ''' Check that the commit, distro hash has been promoted to
        promotion_target as recorded in DLRN. '''

    dlrn_host = stage_info['dlrn_host']
    promotion_target = stage_info['promotion_target']
    commit_hash = stage_info['promotions']['promotion_candidate']['commit_hash']
    distro_hash = stage_info['promotions']['promotion_candidate']['distro_hash']

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


def query_container_registry_promotion(stage_info):
    ''' Check that the hash containers have been pushed to the
        promotion registry with the promotion_target tag. '''

    # TODO(gcerami) Retain the possibility to specify custom values easily
    registry_rdo = stage_info['registries']['source']['host']
    registry_docker_io = stage_info['registries']['targets'][0]
    promotion_target = stage_info['promotion_target']
    full_hash = stage_info['promotions']['promotion_candidate']['full_hash']
    # logger = logging.getLogger('TestPromoter')
    # docker_client = docker.from_env()
    missing_images = []
    if 'localhost' in registry_rdo:
        for line in stage_info['containers']:
            # TODO(gcerami) we should check that manifests are there, and
            # contain the proper information
            reg_url = "http://{}/v2/{}/manifests/{}".format(
                registry_docker_io, line, full_hash
            )
            try:
                url_lib.urlopen(reg_url)
            except url_lib.HTTPError:
                print("Image not found")
                missing_images.append((line, full_hash))
            reg_url = "http://{}/v2/{}/manifests/{}".format(
                registry_docker_io, line, promotion_target
            )
            try:
                url_lib.urlopen(reg_url)
            except url_lib.HTTPError:
                print("Image with named tag not found")
                missing_images.append((line, full_hash))
    else:
        # TODO: how to verify promoter containers
        print("Compare images tagged with hash and promotion target:")

    assert missing_images == [], "Images are missing"


def compare_tagged_image_hash(stage_info):
    ''' Ensure that the promotion target images directory
        is a soft link to the promoted full hash images directory. '''

    images_base_dir = stage_info['overcloud_images']['base_dir']
    user = stage_info['overcloud_images']['user']
    key_path = stage_info['overcloud_images']['key_path']
    distro = stage_info['distro']
    release = stage_info['release']
    promotion_target = stage_info['promotion_target']
    full_hash = stage_info['promotions']['promotion_candidate']['full_hash']

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


def parse_promotion_logs(stage_info):
    ''' Check that the promotion logs have the right
        strings printed for the promotion status '''

    logfile = stage_info['logfile']
    release = stage_info['release']
    promotion_target = stage_info['promotion_target']
    full_hash = stage_info['promotions']['promotion_candidate']['full_hash']
    commit_hash = stage_info['promotions']['promotion_candidate']['commit_hash']
    distro_hash = stage_info['promotions']['promotion_candidate']['distro_hash']
    logger = logging.getLogger('TestPromoter')
    logger.debug("Open promoter file for reading")

    full_hash = get_full_hash(commit_hash, distro_hash)
    # Check if the logfile passed is web hosted
    if 'http' in logfile:
        from bs4 import BeautifulSoup
        logger.debug("Reading web hosted log file")
        url = url_lib.request.urlopen(logfile).read()
        soup = BeautifulSoup(url, 'html.parser')
        logfile_contents = soup.get_text()
    else:
        logger.debug("Reading local log file")
        with open(logfile, 'r') as lf:
            logfile_contents = lf.read()

    # Check that the promoter process finished
    error_message = "Promoter never finished"
    assert 'promoter FINISHED' in logfile_contents, error_message

    # We have a list of hashes at our disposal, we know which one
    # will have to fail, and which one will have to pass
    # We can do all in the same pass
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
    fail_pattern = re.compile(
        r'promoter Skipping promotion of '
        + r'{\'timestamp\': (\d+), \'distro_hash\': \''
        + re.escape(distro_hash) + r'\', (.*) \'full_hash\': \''
        + re.escape(full_hash)
        + r'\', \'repo_hash\': \''
        + re.escape(full_hash) + r'\', \'commit_hash\': \''
        + re.escape(commit_hash) + r'\'}')

    for commit in stage_info['commits']:
        promotion_candidate = stage_info['promotions']['promotion_candidate']
        if commit['full_hash'] == promotion_candidate['full_hash']:
            # This commit is supposed succeed
            # Check strings for passing hashes
            print("Status Passing:")
            # Build pattern for successful promotion
            for pattern in success_patterns:
                success_pattern_search = pattern.search(logfile_contents)
                error_message = "Success text pattern not found - %s" % pattern
                assert success_pattern_search.group(), error_message

        failed_attempt = stage_info['promotions']['failed_attempt']
        if commit['full_hash'] == failed_attempt['full_hash']:
            # This commit is supposed to fail

            # Check string for failing hashes
            print("Status Failing:")
            # Build pattern for failing promotion
            error_message("Fail text pattern not found - %s" % fail_pattern)
            fail_pattern_search = fail_pattern.search(logfile_contents)
            assert fail_pattern_search.group(), error_message


def main():

    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger("TestPromoter")
    log.setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser(
        description='Pass a config file.')
    parser.add_argument('--stage-info-file', default="/tmp/stage-info.yaml")
    args = parser.parse_args()

    with open(args.stage_info_path) as si:
        stage_info = yaml.safe_load(si)

    check_dlrn_promoted_hash(stage_info)
    query_container_registry_promotion(stage_info)
    compare_tagged_image_hash(stage_info)
    parse_promotion_logs(stage_info)


if __name__ == "__main__":
    main()
