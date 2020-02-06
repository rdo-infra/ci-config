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
import pprint
import os
import re
import stat
try:
    import urllib2 as url_lib
except ImportError:
    import urllib.request as url_lib
import yaml

from dlrn_interface import DlrnHash

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("promoter-integation-checks")
log.setLevel(logging.DEBUG)


def check_dlrn_promoted_hash(stage_info=None, **kwargs):
    """ Check that the commit, distro hash has been promoted to
        promotion_target as recorded in DLRN. """
    if stage_info is not None:
        # We are checking a stage
        api_url = stage_info['dlrn']['server']['api_url']
        promotion_target = stage_info['dlrn']['promotion_target']
        candidate_commit = \
            stage_info['dlrn']['promotions']['promotion_candidate']
        candidate_hash = DlrnHash(source=candidate_commit)

        logger = logging.getLogger('TestIntegrationChecks')
        api_client = dlrnapi_client.ApiClient(host=api_url)
        dlrn_client = dlrnapi_client.DefaultApi(api_client=api_client)
        params = dlrnapi_client.PromotionQuery()
        params.limit = 1
        params.promote_name = promotion_target
    else:
        # We are checking production server
        # TODO(gcerami) implement this branch ?
        pass

    try:
        api_response = dlrn_client.api_promotions_get(params)
        logger.debug(api_response)
    except dlrnapi_client.rest.ApiException:
        logger.error('Exception when calling api_promotions_get: %s',
                     dlrnapi_client.rest.ApiException)
        raise

    error_msg = "No promotions for hash {}".format(candidate_hash)
    assert api_response != [], error_msg
    promotion_hash = DlrnHash(source=api_response[0])
    error_message = ("Expected full hash: {}"
                     " has not been promoted to {}."
                     "".format(promotion_hash.full_hash, promotion_target))
    conditions = [(promotion.promote_name == promotion_target)
                  for promotion in api_response]
    assert any(conditions), error_message


def query_container_registry_promotion(stage_info=None, **kwargs):
    """ Check that the hash containers have been pushed to the
        promotion registry with the promotion_target tag. """

    # TODO(gcerami) Retain the possibility to specify custom values easily
    if stage_info is not None:
        registry_target = stage_info['registries']['targets'][0]['host']
        promotion_target = stage_info['dlrn']['promotion_target']
        candidate_dict = stage_info['dlrn']['promotions']['promotion_candidate']
        candidate_hash = DlrnHash(source=candidate_dict)
        missing_images = []
        no_ppc = stage_info.get('ppc_manifests', True)
        no_ppc = stage_info.get('ppc_manifests', False)
        pprint.pprint(stage_info)
        for line in stage_info['containers']['images']:
            name, tag = line.split(":")
            reg_url = "http://{}/v2/{}/manifests/{}".format(
                registry_target, name, tag
            )
            print("Checking for promoted container hash: " + reg_url)
            try:
                url_lib.urlopen(reg_url)
            except url_lib.HTTPError:
                if no_ppc and '_ppc64le' in tag:
                    print("(expected - ppc manifests disabled)"
                          "Image not found - " + line)
                else:
                    print("Image not found - " + line)
                    missing_images.append(line)
            # For the full_hash lines only, check that there is
            # an equivalent promotion_target entry
            if tag == candidate_hash.full_hash:
                reg_url = "http://{}/v2/{}/manifests/{}".format(
                    registry_target, name, promotion_target
                )
                print("Checking for promoted container tag: " + reg_url)
                try:
                    url_lib.urlopen(reg_url)
                except url_lib.HTTPError:
                    print("Image with named tag not found - " + line)
                    promo_tgt_line = line.replace(candidate_hash.full_hash,
                                                  promotion_target)
                    missing_images.append(promo_tgt_line)
    else:
        # We are checking production
        # TODO: how to verify promoter containers
        print("Compare images tagged with hash and promotion target:")

    print(missing_images)
    assert missing_images == [], "Images are missing"


def compare_tagged_image_hash(stage_info=None, **kwargs):
    """ Ensure that the promotion target images directory
        is a soft link to the promoted full hash images directory. """

    if stage_info is not None:
        # We are cheking a stage
        distro_name = stage_info['main']['distro_name']
        distro_version = stage_info['main']['distro_version']
        distro = "{}{}".format(distro_name, distro_version)
        release = stage_info['main']['release']
        target_label = stage_info['dlrn']['promotion_target']
        images_top_root = stage_info['overcloud_images']['root']
        images_top_root = images_top_root.rstrip("/")
        images_root = os.path.join(images_top_root, distro, release,
                                   "rdo_trunk")
        promotion_link = os.path.join(images_root, target_label)
        candidate_dict = stage_info['dlrn']['promotions']['promotion_candidate']
        candidate_hash = DlrnHash(source=candidate_dict)
        promotion_dir = os.path.join(images_root, candidate_hash.full_hash)
        current_dict = stage_info['dlrn']['promotions']['currently_promoted']
        current_hash = DlrnHash(source=current_dict)
        previous_dict = stage_info['dlrn']['promotions']['previously_promoted']
        previous_label = previous_dict['name']
        previous_link = os.path.join(images_root, previous_label)
        previous_dir = os.path.join(images_root, current_hash.full_hash)

        rl_module = os
    else:
        # We are checking production
        # FIXME(gerami) this branch needs revisiting
        images_base_dir = kwargs['image_base']
        user = kwargs['user']
        key_path = kwargs['key_path']
        # promotion_target = args[3]
        # full_hash = args[4]
        # release = kwargs['release']
        print("Install required for nonstaging env")
        import pysftp
        sftp = pysftp.Connection(
            host=images_base_dir,
            username=user, private_key=key_path)

        # images_dir = os.path.join(
        #    '/var/www/html/images',
        #    release, 'rdo_trunk')
        rl_module = sftp

    try:
        file_mode = rl_module.lstat(promotion_link).st_mode
        assert True
    except OSError:
        assert False, "No link was created"

    assert stat.S_ISLNK(file_mode), "promoter dir is not a symlink"
    error_msg = "Linked wrong dir"
    assert rl_module.readlink(promotion_link) == promotion_dir, error_msg
    try:
        file_mode = rl_module.lstat(previous_link).st_mode
        assert True
    except OSError:
        assert False, "No link was created"

    assert stat.S_ISLNK(file_mode), "Promoted dir is not a symlink"
    assert rl_module.readlink(
        previous_link) == previous_dir, "No previous dir create"


def parse_promotion_logs(stage_info=None, **kwargs):
    """ Check that the promotion logs have the right
        strings printed for the promotion status """

    if stage_info is not None:
        # We are checking a stage
        logfile = stage_info['main']['logfile']
        release = stage_info['main']['release']
        promotion_target = stage_info['dlrn']['promotion_target']
        candidate_dict = stage_info['dlrn']['promotions']['promotion_candidate']
        candidate_hash = DlrnHash(source=candidate_dict)
        candidate_name = \
            stage_info['dlrn']['promotions']['promotion_candidate']['name']
        commits = stage_info['dlrn']['commits']
        promotion_candidate = \
            stage_info['dlrn']['promotions']['promotion_candidate']

        log.debug("Reading local log file")
        with open(logfile, 'r') as lf:
            logfile_contents = lf.read()
    else:
        # We are checking production
        logfile = kwargs['logfile']
        from bs4 import BeautifulSoup
        log.debug("Reading web hosted log file")
        url = url_lib.request.urlopen(logfile).read()
        soup = BeautifulSoup(url, 'html.parser')
        logfile_contents = soup.get_text()

    # Check that the promoter process finished
    error_message = "Promoter never finished"
    assert 'promoter FINISHED' in logfile_contents, error_message

    # We have a list of hashes at our disposal, we know which one
    # will have to fail, and which one will have to pass
    # We can do all in the same pass
    success_pattern_container = re.compile(
        r'promoter Promoting the container images for dlrn hash '
        + re.escape(candidate_hash.commit_hash))
    success_pattern_images = re.compile(
        r'Promoting the qcow image for dlrn hash '
        + re.escape(candidate_hash.full_hash) + r' on '
        + re.escape(release) + r' to '
        + re.escape(promotion_target))
    success_pattern = \
        re.compile("Successful jobs for.*{}"
                   "".format(re.escape(candidate_hash.commit_hash)))
    success_pattern_target = re.compile(
        "promoter SUCCESS promoting centos7-"
        + re.escape(release) + ' '
        + re.escape(candidate_name) + r" as "
        + re.escape(promotion_target))

    success_patterns = [
        success_pattern,
        success_pattern_images,
        success_pattern_container,
        success_pattern_target,
    ]

    for commit in commits:
        if commit['full_hash'] == promotion_candidate['full_hash']:
            # This commit is supposed succeed
            # Check strings for passing hashes
            print("Status Passing: " + commit['full_hash'])
            # Build pattern for successful promotion
            for check_pattern in success_patterns:
                success_pattern_search = check_pattern.search(logfile_contents)
                error_message = "Pattern not found- %s" % check_pattern.pattern
                assert success_pattern_search is not None, error_message


def main():

    parser = argparse.ArgumentParser(
        description='Pass a config file.')
    parser.add_argument('--stage-info-file', default="/tmp/stage-info.yaml")
    args = parser.parse_args()

    with open(args.stage_info_file) as si:
        stage_info = yaml.safe_load(si)

    print('Running test: check_dlrn_promoted_hash')
    check_dlrn_promoted_hash(stage_info=stage_info)
    print('Running test: query_container_registry_promotion')
    query_container_registry_promotion(stage_info=stage_info)
    print('Running test: compare_tagged_image_hash')
    compare_tagged_image_hash(stage_info=stage_info)
    print('Running test: parse_promotion_logs')
    parse_promotion_logs(stage_info=stage_info)


if __name__ == "__main__":
    main()
