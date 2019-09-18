#!/usr/bin/env python
"""
This script tests the steps of the promoter workflow.
 - Checks the dlrn API that tha hash under test has been promoted to the promotion target
 - Checks that images are uploaded with that hash and linked to promotion target
 - Checks that containers with that hash are pushed to repo 2
 - Checks the promoter logs for expected strings

See https://github.com/rdo-infra/ci-config/blob/master/ci-scripts/dlrnapi_promoter/dlrnapi_promoter.py
"""

import datetime
import docker
import filecmp
import logging
import os
import re
import requests
import pysftp

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
        try:
            source_image = docker_client.images.get(images_promoted)
        except docker.errors.ImageNotFound:
            registry_data = docker_client.images.get_registry_data(
                image_promoted)
           source_image = registry_data.pull(platform="x86_64")

def compare_tagged_image_hash(overcloud_images_base_dir, distro, release, promotion_target, commit_hash, distro_hash):
    ''' Ensure that the promotion target images directory
        is a soft link to the promoted full hash images directory. '''

    logger = logging.getLogger('TestPromoter')
    full_hash = get_full_hash(commit_hash, distro_hash)
    image_dir = os.path.join(overcloud_images_base_dir, distro,
                                     release, "rdo_trunk")

    image_dict = {}
    image_tags = [full_hash, promotion_target]
    for i in image_tags:
        # Get the dir contents
        images_dir_tag = os.path.join(image_dir, i)
        if 'overcloud_images' not in overcloud_images_base_dir:
            images_dir_tag_url = urllib.request.urlopen(images_dir_tag).read()
            images_dir_tag_url_contents = BeautifulSoup(images_dir_tag_url, 'html.parser').get_text()
            image_dict[i] = images_dir_tag_url_contents
            try:
                assert image_dict[full_hash] == image_dict[promotion_target].replace(promotion_target, full_hash, 2)
            except AssertionError as e:
                print("Full hash and promotion target contents are not the same.")
                raise e

            # Check the md5 sum of the full_hash and promotion target overcloud images
            if 'http' in overcloud_images_base_dir:
                md5_dict = {}
                for i in image_tags:
                    md5_req = requests.get(os.path.join(image_dir, i, 'overcloud-full.tar.md5'))
                    os.makedirs(os.path.join('/tmp/overcloud_images/', i))
                    md5_dict[i] = os.path.join('/tmp/overcloud_images/', i, 'overcloud-full.tar.md5')
                    open(md5_dict[i], 'wb').write(md5_req.content)
                filecmp.cmp(md5_dict[full_hash], md5_dict[promotion_target])
        else:
            # Check that the promotion_target dir is a soft link
            try:
                assert full_hash == os.readlink(os.path.join(image_dir, promotion_target))
            except AssertionError as e:
                 print("Promotion target dir is not a softlink of the full hash dir.")
                 raise e

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

    if status == 'success':
        # Check strings for passing hashes
        print("Status Passing:")
        # Build pattern for successful promotion
        success_pattern_container = re.compile(r'promoter Promoting the container images for dlrn hash ' + re.escape(commit_hash))
        # TODO: success_pattern_images =
        success_pattern = re.compile(r'promoter Successful jobs for {\'timestamp\': (\d+), \'distro_hash\': \''  + re.escape(distro_hash) + r'\', (.*) \'full_hash\': \'' + re.escape(full_hash) + r'\', \'repo_hash\': \'' + re.escape(full_hash) + r'\', \'commit_hash\': \'' + re.escape(commit_hash) + r'\'}')
        success_pattern_search = success_pattern.search( logfile_contents )
        print(success_pattern_search.group())
        success_pattern_container_search = success_pattern_container.search( logfile_contents )
        print(success_pattern_container_search.group())

    elif status == 'failed':
        # Check string for failing hashes
        print("Status Failing:")
        # Build pattern for failing promotion
        fail_pattern = re.compile(r'promoter Skipping promotion of {\'timestamp\': (\d+), \'distro_hash\': \''  + re.escape(distro_hash) + r'\', (.*) \'full_hash\': \'' + re.escape(full_hash) + r'\', \'repo_hash\': \'' + re.escape(full_hash) + r'\', \'commit_hash\': \'' + re.escape(commit_hash) + r'\'}')
        fail_pattern_search = fail_pattern.search( logfile_contents )
        print(fail_pattern_search.group())


def main():

    #logging.basicConfig(level=logging.DEBUG)
    #log = logging.getLogger("TestPromoter")
    #log.setLevel(logging.DEBUG)

    ## Create a webserver to test promotion logs and images
    #import http.server
    #import socketserver

    #PORT = 8080
    #Handler = http.server.SimpleHTTPRequestHandler
    #httpd = SocketServer.TCPServer(("", PORT), Handler)
    #print "serving at port", PORT
    #httpd.serve_forever()

    # Move the promoter logs and images to be accessible via http

    #parse_promotion_logs('http://xx/centos7_rocky.log', '214ee82e455ebad5aa41dd3599cd82576bbdb9dc', '798f6b1aca244c3dd2ab5634f0a8947b2c3c8ffc', 'failed')
    #parse_promotion_logs('http://xx/centos7_master.log-20190914', '4e2116ddc27bd6f381721f058f47322245141a39', 'bbaf1d8e7dd70fd6caf6ce80315e9f48b522ad97', 'success')
    #compare_tagged_image_hash('/tmp', 'centos7', 'master', 'current-tripleo', '4e2116ddc27bd6f381721f058f47322245141a39', 'bbaf1d8e7dd70fd6caf6ce80315e9f48b522ad97')
    #check_dlrn_promoted_hash('https://xx/xx', 'current-tripleo', '4e2116ddc27bd6f381721f058f47322245141a39', 'bbaf1d8e7dd70fd6caf6ce80315e9f48b522ad97')

if __name__ == "__main__":
    main()
