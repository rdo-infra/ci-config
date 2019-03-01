#!/usr/bin/env python

import logging

from dlrnapi_client.rest import ApiException
import dlrnapi_client
import sys


def check_trigger_condition(dlrn, promotion_name, wait_job_name,
                            launch_job_name):

    params = dlrnapi_client.PromotionQuery()
    params.promote_name = promotion_name
    api_response = dlrn.api_promotions_get(params)
    last_promotion = api_response[0]
    params = dlrnapi_client.Params2()
    params.distro_hash = last_promotion.distro_hash
    params.commit_hash = last_promotion.commit_hash
    api_response = dlrn.api_repo_status_get(params)
    wait_job = None
    launch_job = None
    for status in api_response:
        if wait_job_name == status.job_id:
            wait_job = status
        elif launch_job_name == status.job_id:
            launch_job = status

    # Trigger if job is not already trigger and wait job is fine
    return launch_job is None and wait_job is not None and wait_job.success


if __name__ == '__main__':
    dlrnapi_url = "https://trunk.rdoproject.org/api-centos-master-uc"
    promotion_name = 'tripleo-ci-testing'
    wait_job_name = 'periodic-tripleo-centos-7-master-containers-build'
    launch_job_name = 'test-connection-to-hardware'
    client = dlrnapi_client.ApiClient(host=dlrnapi_url)
    dlrn = dlrnapi_client.DefaultApi(api_client=client)
    if not check_trigger_condition(dlrn, promotion_name, wait_job_name,
                                   launch_job_name):
        sys.exit(1)
