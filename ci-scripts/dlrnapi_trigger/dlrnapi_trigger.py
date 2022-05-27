#!/usr/bin/env python

import argparse
import logging
import sys

import dlrnapi_client

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(process)d'
    ' %(levelname)-8s %(name)s %(message)s')


def check_trigger_condition(dlrn, promotion_name, wait_job_name,
                            launch_job_name):
    """
    Check if launch job has to run looking for the wait job at the latest
    DLRN promotion, the wait job has to be at success state.

    This just look at latest promotion and also don't retrigger if the
    launch_job state is not success.

    This uses to calls to the dlrnapi_client.DefaultApi:
        - api_promotions_get to get the newest  'Promotion'
        - api_repo_status_get to get the jobs from the 'Promotion'

    Parameters
    ----------
    dlrn : dlrnapi_client.DefaultApi
        The dlrn api impl to look for promotions and repo status
    promotion_name: str
        The promotion name to use, tripleo-ci-testing for example
    wait_job_name: str
        Name of the job that have to finish with success state to for
        the trigger condition to be True
    launch_job_name: str
        Name of the job that we want to trigger.

    Returns
    -------
    bool
        It will be True if the launch_job_name has to be triggered false
        otherwise
    """
    logger = logging.getLogger("dlrn-trigger")
    params = dlrnapi_client.PromotionQuery()
    params.promote_name = promotion_name
    api_response = dlrn.api_promotions_get(params)
    last_promotion = api_response[0]
    logger.debug("Selected promotion: {}".format(last_promotion))
    params = dlrnapi_client.Params2()
    params.distro_hash = last_promotion.distro_hash
    params.commit_hash = last_promotion.commit_hash
    api_response = dlrn.api_repo_status_get(params)
    logger.debug("CI status from promotion: {}".format(api_response))
    wait_job = None
    launch_job = None
    # Select the first ocurrence of wait and launch job
    for status in api_response:
        if wait_job is None and status.job_id == wait_job_name:
            wait_job = status
        elif launch_job is None and status.job_id == launch_job_name:
            launch_job = status
    logger.info("Selected wait job build: {}".format(wait_job))
    logger.info("Selected launch job build: {}".format(launch_job))
    # Trigger if job is not already trigger and wait job is fine
    return launch_job is None and wait_job is not None and wait_job.success


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Check condition at DLRN to trigger job")
    parser.add_argument(
        '--dlrn-url',
        default="https://trunk.rdoproject.org/api-centos-master-uc")
    parser.add_argument('--promotion-name', default="tripleo-ci-testing")
    parser.add_argument(
        '--wait-job',
        default="periodic-tripleo-centos-8-master-containers-build-push")
    parser.add_argument('--launch-job', default="test-connection-to-hardware")
    args = parser.parse_args()

    client = dlrnapi_client.ApiClient(host=args.dlrn_url)
    dlrn = dlrnapi_client.DefaultApi(api_client=client)
    if not check_trigger_condition(dlrn, args.promotion_name, args.wait_job,
                                   args.launch_job):
        sys.exit(1)
