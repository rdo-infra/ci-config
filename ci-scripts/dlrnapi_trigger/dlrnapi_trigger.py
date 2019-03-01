#!/usr/bin/env python

import argparse
import logging

from dlrnapi_client.rest import ApiException
import dlrnapi_client
import sys

logging.basicConfig(level=logging.DEBUG)

def check_trigger_condition(dlrn, promotion_name, wait_job_name,
                            launch_job_name):
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
    for status in api_response:
        if wait_job_name == status.job_id:
            wait_job = status
        elif launch_job_name == status.job_id:
            launch_job = status
    logger.info("Wait job status: {}".format(wait_job))
    logger.info("Launch job status: {}".format(launch_job))
    # Trigger if job is not already trigger and wait job is fine
    return launch_job is None and wait_job is not None and wait_job.success


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(
                description="Check condition at DLRN to trigger job")
    parser.add_argument('--dlrn-url', default="https://trunk.rdoproject.org/api-centos-master-uc")
    parser.add_argument('--promotion-name', default="tripleo-ci-testing")
    parser.add_argument('--wait-job', default="periodic-tripleo-centos-7-master-containers-build")
    parser.add_argument('--launch-job', default="test-connection-to-hardware")
    args = parser.parse_args()

    client = dlrnapi_client.ApiClient(host=args.dlrn_url)
    dlrn = dlrnapi_client.DefaultApi(api_client=client)
    if not check_trigger_condition(dlrn, args.promotion_name, args.wait_job,
                                   args.launch_job):
        sys.exit(1)
