#!/usr/bin/env python
"""
This file contains the function used in the promoter.
The functions here WILL NOT BE TOUCHED by the new design, this code will stay
until the new modularized code is proven to be stable.
The current workflow will import function from here when needed.
Then the call in the main file will be gradually replaced with
the new code.
"""

from __future__ import print_function
from datetime import datetime
import configparser
import logging
import logging.handlers
import os
import subprocess
import sys

from dlrnapi_client.rest import ApiException
import dlrnapi_client

# start_named_hashes - named hashes at promotion start
# can check they are not changed before we push containers/images/links.
# {'current-tripleo': 'xyz', 'previous-current-tripleo': 'abc' ... }
# https://tree.taiga.io/project/tripleo-ci-board/task/1325
start_named_hashes = {}


def fetch_current_named_hashes(release, promote_from, dlrn):
    ''' Get latest known named hashes from dlrn
        Returns a dictionary with name to hash {'current-tripleo': 'xyz', '''
    named_hashes_result = {}

    for promote_name in promote_from.keys():
        latest_named = fetch_hashes(dlrn, promote_name, 1)
        full_hash = '{0}_{1}'.format(
                  latest_named['commit_hash'], latest_named['distro_hash'][:8])
        named_hashes_result.update({promote_name: full_hash})

    return named_hashes_result


def check_named_hashes_unchanged(release, promote_from, dlrn):
    ''' Fetch latest named hashes and compare to start_named_hashes
        If they are different log error and raise Exception
    '''
    logger = logging.getLogger('promoter')
    latest_named_hashes = fetch_current_named_hashes(
                                                   release, promote_from, dlrn)
    if latest_named_hashes != start_named_hashes:
        logger.error('ERROR: Aborting promotion named hashes changed since '
                     'promotion started. Hashes at start: %s. Hashes now: %s ',
                     start_named_hashes, latest_named_hashes)
        raise Exception("Named Hashes Changed!")


def check_promoted(dlrn, link, hashes):
    ''' check if hashes has ever been promoted to link'''
    logger = logging.getLogger('promoter')
    params = dlrnapi_client.PromotionQuery()
    params.commit_hash = hashes['commit_hash']
    params.distro_hash = hashes['distro_hash']
    try:
        api_response = dlrn.api_promotions_get(params)
    except ApiException:
        logger.error('Exception when calling api_promotions_get: %s',
                     ApiException)
        raise
    return any([(promotion.promote_name == link) for promotion in api_response])


def fetch_hashes(dlrn, link, count=1):
    '''Get the commit and distro hashes for a specific promotion link'''
    logger = logging.getLogger('promoter')
    params = dlrnapi_client.PromotionQuery()
    params.promote_name = link
    try:
        api_response = dlrn.api_promotions_get(params)
    except ApiException:
        logger.error('Exception when calling api_promotions_get: %s',
                     ApiException)
        raise
    if len(api_response) == 0:
        return None
    if count == 1:
        return api_response[0].to_dict()
    else:
        unduplicated_response = []
        for hashes in api_response:
            hashes = hashes.to_dict()
            existing_hashes = \
                [(ex_hashes['commit_hash'], ex_hashes['distro_hash'])
                    for ex_hashes in unduplicated_response]
            if (hashes['commit_hash'],
                    hashes['distro_hash']) not in existing_hashes:
                unduplicated_response.append(hashes)

        if count == -1:
            return unduplicated_response

        return unduplicated_response[:count]


def fetch_jobs(dlrn, hash_values):
    '''Fetch the successfully finished jobs for a specific DLRN hash'''
    logger = logging.getLogger('promoter')
    params = dlrnapi_client.Params2()
    params.commit_hash = hash_values['commit_hash']
    params.distro_hash = hash_values['distro_hash']
    params.success = str(True)

    try:
        api_response = dlrn.api_repo_status_get(params)
    except ApiException:
        logger.error('Exception when calling api_repo_status_get: %s',
                     ApiException)
        raise
    logger.debug('Successful jobs for %s:', hash_values)
    for result in api_response:
        logger.debug('%s at %s, logs at %s', result.job_id,
                     datetime.fromtimestamp(result.timestamp).isoformat(),
                     result.url)
    return [details.job_id for details in api_response]


def promote_link(dlrn, hash_values, link):
    '''Promotes a set of hash values as a named link using DLRN API'''
    logger = logging.getLogger('promoter')
    current_hashes = fetch_hashes(dlrn, link)
    # Save current hash as previous-$link
    if current_hashes is not None:
        params = dlrnapi_client.Promotion()
        params.commit_hash = current_hashes['commit_hash']
        params.distro_hash = current_hashes['distro_hash']
        params.promote_name = "previous-" + link
        try:
            dlrn.api_promote_post(params)
        except ApiException:
            logger.error('Exception when calling api_promote_post: %s'
                         ' to store current hashes as previous',
                         ApiException)
            raise
    params = dlrnapi_client.Promotion()
    params.commit_hash = hash_values['commit_hash']
    params.distro_hash = hash_values['distro_hash']
    params.promote_name = link
    try:
        dlrn.api_promote_post(params)
    except ApiException:
        logger.error('Exception when calling api_promote_post: %s',
                     ApiException)
        raise


def setup_logging(log_file):
    '''Setup logging for the script'''
    logger = logging.getLogger('promoter')
    logger.setLevel(logging.DEBUG)
    log_handler = logging.handlers.WatchedFileHandler(
        os.path.expanduser(log_file))
    log_formatter = logging.Formatter('%(asctime)s %(process)d '
                                      '%(levelname)-8s %(name)s %(message)s')
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)


def tag_containers(new_hashes, distro, release, promote_name, manifest_push,
                   target_registries_push):
    logger = logging.getLogger('promoter')
    env = os.environ
    relpath = "ci-scripts/dlrnapi_promoter"
    script_root = os.path.abspath(sys.path[0]).replace(relpath, "")
    logfile = os.path.abspath(os.path.join(
        script_root,
        "../promoter_logs/container-push/%s.log" %
        datetime.now().strftime("%Y%m%d-%H%M%S")))
    env['RELEASE'] = release
    env['COMMIT_HASH'] = new_hashes['commit_hash']
    env['DISTRO_HASH'] = new_hashes['distro_hash']
    env['FULL_HASH'] = new_hashes['full_hash']
    env['PROMOTE_NAME'] = promote_name
    env['SCRIPT_ROOT'] = script_root
    distro_name, distro_version = distro
    env['DISTRO_NAME'] = distro_name
    env['DISTRO_VERSION'] = distro_version
    promote_playbook = (
        script_root + 'ci-scripts/container-push/container-push.yml'
    )

    push_opts = ("-e manifest_push=%s -e target_registries_push=%s"
                 "" % (manifest_push, target_registries_push))
    try:
        logger.info('Promoting the container images for dlrn hash %s on '
                    '%s to %s', new_hashes['commit_hash'], release,
                    promote_name)

        # Use single string to make it easy to copy/paste from logs
        cmd = "env " \
            "ANSIBLE_LOG_PATH=%s RELEASE=%s " \
            "COMMIT_HASH=%s DISTRO_HASH=%s FULL_HASH=%s " \
            "PROMOTE_NAME=%s SCRIPT_ROOT=%s DISTRO_NAME=%s DISTRO_VERSION=%s " \
            "ansible-playbook %s %s" % (
                logfile,
                release, new_hashes['commit_hash'], new_hashes['distro_hash'],
                new_hashes['full_hash'], promote_name, script_root, distro_name,
                distro_version, push_opts, promote_playbook
            )
        logger.info('Running: %s', cmd)
        container_logs = \
            subprocess.check_output(
                cmd.split(" "),
                stderr=subprocess.STDOUT).split("\n")
        for line in container_logs:
            logger.info(line)
    except subprocess.CalledProcessError as ex:
        logger.error('CONTAINER IMAGE UPLOAD FAILED LOGS BELOW:')
        logger.error(ex.output)
        logger.exception(ex)
        logger.error('END OF CONTAINER IMAGE UPLOAD FAILURE')
        raise


def tag_qcow_images(new_hashes, distro, release, promote_name):
    logger = logging.getLogger('promoter')
    relpath = "ci-scripts/dlrnapi_promoter"
    script_root = os.path.abspath(sys.path[0]).replace(relpath, "")
    promote_script = script_root + 'ci-scripts/promote-images.sh'
    full_hash = new_hashes['full_hash']
    try:
        logger.info('Promoting the qcow image for dlrn hash %s on %s to %s',
                    full_hash, release, promote_name)
        qcow_logs = subprocess.check_output(
            ['bash', promote_script,
             '--distro', distro[0],
             '--distro-version', distro[1],
             release, full_hash,
             promote_name],
            stderr=subprocess.STDOUT).split("\n")
        for line in qcow_logs:
            logger.info(line)
    except subprocess.CalledProcessError as ex:
        logger.error('QCOW IMAGE UPLOAD FAILED LOGS BELOW:')
        logger.error(ex.output)
        logger.exception(ex)
        logger.error('END OF QCOW IMAGE UPLOAD FAILURE')
        raise


def get_latest_hashes(api, promote_name, current_name, latest_hashes_count):
    '''Get and filter eligible hashes for promotion'''
    logger = logging.getLogger('promoter')

    candidate_hashes_list = fetch_hashes(
        api,
        current_name,
        count=latest_hashes_count)

    if candidate_hashes_list is None:
        logger.error('Failed to fetch any hashes for %s, skipping promotion',
                     current_name)
        return []
    else:
        logger.debug('Hashes fetched (tried to get the last %d): %s',
                     latest_hashes_count, candidate_hashes_list)
        candidate_hashes_list.sort(
            key=lambda hashes: hashes['timestamp'],
            reverse=True)

    # This will be a map of recent hashes candidate for promotion. We'll map
    # here the timestamp for each promotion to promote name, if any
    candidate_hashes = {}
    for hashes in candidate_hashes_list:
        full_hash = "%s_%s" % (hashes['commit_hash'], hashes['distro_hash'])
        candidate_hashes[full_hash] = {}
        candidate_hashes[full_hash][current_name] = hashes['timestamp']

    old_hashes = fetch_hashes(api, promote_name, count=-1)
    if old_hashes is None:
        logger.warning('Failed to fetch hashes for %s, no previous '
                       'promotion or typo in the link name',
                       promote_name)
    else:
        for hashes in old_hashes:
            full_hash = "%s_%s" % (
                hashes['commit_hash'], hashes['distro_hash'])
            # it may happen that an hash appears in this list, but it's not from
            # our list of candindates. If this happens we're just ignoring it
            if full_hash in candidate_hashes:
                candidate_hashes[full_hash][promote_name] = hashes['timestamp']

    # returning only the hashes younger than the latest promoted
    # this list is already in reverse time order
    for index, hashes in enumerate(candidate_hashes_list):
        full_hash = "%s_%s" % (hashes['commit_hash'], hashes['distro_hash'])
        if promote_name in candidate_hashes[full_hash]:
            logger.info('Current "%s" hash is %s' % (promote_name, hashes))
            candidate_hashes_list = candidate_hashes_list[:index]
            break

    if candidate_hashes_list:
        logger.debug(
            'Remaining hashes after removing ones older than the '
            'currently promoted: %s', candidate_hashes_list)
    else:
        logger.debug(
            'No remaining hashes after removing ones older than the '
            'currently promoted')

    return candidate_hashes_list


def promote_all_links(
        api,
        promote_from,
        job_reqs,
        dry_run,
        distro,
        release,
        latest_hashes_count,
        api_url,
        manifest_push,
        target_registries_push):
    '''Promote DLRN API links as a different one when all jobs are
    successful'''
    logger = logging.getLogger('promoter')

    # promote_all_links - labels loop
    for promote_name, current_name in promote_from.items():
        logger.info('Trying to promote %s to %s', current_name, promote_name)
        # promote_all_links - candidate hashes selection
        # Cycle over latest unpromoted hashes
        for new_hashes in get_latest_hashes(api, promote_name, current_name,
                                            latest_hashes_count):
            logger.info('Checking hash %s from %s for promotion criteria',
                        new_hashes, current_name)
            new_hashes['full_hash'] = \
                '{0}_{1}'.format(new_hashes['commit_hash'],
                                 new_hashes['distro_hash'][:8])
            successful_jobs = set(fetch_jobs(api, new_hashes))
            required_jobs = set(job_reqs[promote_name])
            # promote_all_links - label reject condition
            if not required_jobs:
                logger.info(
                    'Skipping promotion of %s from %s to %s, no jobs '
                    'specified in criteria',
                    new_hashes, current_name, promote_name)
                break
            missing_jobs = list(required_jobs - successful_jobs)
            # promote_all_links - hashes reject condition
            if missing_jobs:
                logger.info(
                    'Skipping promotion of %s%s-%s %s from %s to %s, missing '
                    'successful jobs: %s',
                    distro[0], distro[1], release, new_hashes, current_name,
                    promote_name, missing_jobs)
                logger.info('Check Results at:')
                logger.info(
                    '%s \n%s/api/civotes_detail.html?'
                    'commit_hash=%s&distro_hash=%s'.replace(" ", ""),
                    'DETAILED MISSING JOBS: ',
                    api_url,
                    new_hashes['commit_hash'],
                    new_hashes['distro_hash'])
                continue
            # promote_all_links - noop promotion
            if dry_run:
                logger.info('DRY RUN: promotion conditions satisfied, '
                            'skipping promotion of %s-%s %s to %s (%s)',
                            distro, release, current_name,
                            promote_name, new_hashes)
                break
            else:
                # promote_all_links - effective promotion
                try:
                    # ocata does not have containers to upload
                    # this can be removed once ocata is EOL
                    # promote_all_links - containers promotion
                    check_named_hashes_unchanged(release, promote_from, api)
                    if release not in ['ocata']:
                        tag_containers(
                            new_hashes,
                            distro,
                            release,
                            promote_name,
                            manifest_push,
                            target_registries_push)

                    # promote_all_links - qcows promotion
                    # For fedora we just run standalone let's not tag images
                    check_named_hashes_unchanged(release, promote_from, api)
                    distro_name, _ = distro
                    if distro_name != 'fedora':
                        tag_qcow_images(
                            new_hashes,
                            distro,
                            release,
                            promote_name)

                    # promote_all_links - dlrn promotion
                    check_named_hashes_unchanged(release, promote_from, api)
                    promote_link(api, new_hashes, promote_name)
                    logger.info('SUCCESS promoting %s%s-%s %s as %s (%s)',
                                distro[0], distro[1], release, current_name,
                                promote_name, new_hashes)
                    logger.info(
                        '%s \n%s/api/civotes_detail.html?\
                        commit_hash=%s&distro_hash=%s'.replace(" ", ""),
                        'DETAILED SUCCESSFUL STATUS: ',
                        api_url,
                        new_hashes['commit_hash'],
                        new_hashes['distro_hash'])
                    # update start_named_hashes after promotion for other
                    # items in promote_from that we will loop for
                    updated_named_hash = '{0}_{1}'.format(
                        new_hashes['commit_hash'],
                        new_hashes['distro_hash'][:8])
                    global start_named_hashes
                    start_named_hashes.update(
                        {promote_name: updated_named_hash})
                    # stop here, don't try to promote other hashes
                    break
                # promote_all_links - effective promotion failure
                except Exception:
                    logger.info('FAILED promoting %s%s-%s %s as %s (%s)',
                                distro[0], distro[1], release, current_name,
                                promote_name, new_hashes)
                    logger.info(
                        '%s \n%s/api/civotes_detail.html?'
                        'commit_hash=%s&distro_hash=%s'.replace(" ", ""),
                        'DETAILED FAILED STATUS: ',
                        api_url,
                        new_hashes['commit_hash'],
                        new_hashes['distro_hash'])
                    raise


def promoter(config):
    logger = logging.getLogger('promoter')

    distro = (config.get('main', 'distro_name').lower(),
              config.get('main', 'distro_version'))

    release = config.get('main', 'release')
    api_url = config.get('main', 'api_url')

    # No boolean values here, as these are passed directly to ansible-playbook
    # command line
    manifest_push = config.get('main', 'manifest_push', fallback="false")
    target_registries_push = config.get('main', 'target_registries_push',
                                        fallback="true")

    logger.info('STARTED promotion process for release: %s', release)

    try:
        git_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                           cwd=os.path.abspath(sys.path[0]))
        logger.info('Current git hash of repo containing the promoter '
                    'script: %s', git_hash.strip())
    except OSError:
        logger.debug('Failed to get the current git repo hash, check if '
                     'git is installed.')
    except subprocess.CalledProcessError:
        logger.debug('Failed to get the current git repo hash, probably not '
                     'running inside a git repository.')

    # setup the API connection
    dry_run = config.getboolean('main', 'dry_run')
    api_client = dlrnapi_client.ApiClient(host=config.get('main', 'api_url'))
    dlrnapi_client.configuration.username = config.get('main', 'username')
    if os.getenv('DLRNAPI_PASSWORD', None) is None:
        logger.warning('DLRNAPI_PASSWORD env variable is missing or empty, '
                       'promotion attempt will fail!')
    dlrnapi_client.configuration.password = os.getenv('DLRNAPI_PASSWORD', None)
    api_instance = dlrnapi_client.DefaultApi(api_client=api_client)
    latest_hashes_count = config.getint('main', 'latest_hashes_count')
    config.remove_section('main')
    logger.info('Using API URL: %s', api_client.host)

    # load the promote_from data
    promote_from = {k: v for k, v in config.items('promote_from')}
    logger.debug('Attempting to promote these DLRN links: %s',
                 promote_from)
    config.remove_section('promote_from')

    # load the promotion requirements
    job_reqs = {}
    sections = config.sections()
    for section in sections:
        job_reqs[section] = [k for k, v in config.items(section)]
    logger.debug('Promotion requirements loaded: %s', job_reqs)

    global start_named_hashes
    start_named_hashes = fetch_current_named_hashes(
                                           release, promote_from, api_instance)
    logger.info('Named hashes at start of promotion process: %s',
                start_named_hashes)

    promote_all_links(
        api_instance,
        promote_from,
        job_reqs,
        dry_run,
        distro,
        release,
        latest_hashes_count,
        api_url,
        manifest_push,
        target_registries_push)
    logger.info("FINISHED promotion process")


def legacy_main():
    if len(sys.argv) < 2:
        print("Usage: %s <config-file>" % sys.argv[0])
    else:
        config = configparser.SafeConfigParser(allow_no_value=True)
        config.read(sys.argv[1])
        setup_logging(config.get('main', 'log_file'))
        logger = logging.getLogger('promoter')
        try:
            promoter(config)
        except Exception as e:
            logger.exception(e)
