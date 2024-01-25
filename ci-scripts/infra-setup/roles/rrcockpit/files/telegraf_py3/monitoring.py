import logging
import os

import dlrnapi_client
import requests
import yaml
from flask import Flask, abort, jsonify

app = Flask(__name__)

# Use user-provided CA bundle or fallback to system-provided CA bundle.
# Ensure that your CA bundle includes Red Hat's certificate authority,
# because downstream uses self-signed certificates in certificate chain.
# Requests uses certificates from the package certifi by default which
# is missing Red Hat's certificate authority.
CERT_PATH = os.environ.get(
                'CURL_CA_BUNDLE',
                '/etc/pki/ca-trust/extracted/openssl/ca-bundle.trust.crt')

MATRIX = {
    "rhel-9": ["osp17", "osp17-1", "osp18"],
    "rhel-8": ["osp17-1", "osp16-2"],
    "rhel9": ["osp17", "osp17-1", "osp18"],
    "rhel8": ["osp17-1", "osp16-2"],
    "centos9": ["master", "antelope"],
}
REVERSED_MATRIX = {}
for key, values in MATRIX.items():
    for value in values:
        REVERSED_MATRIX.setdefault(value, []).append(key)

DISTROS = list(MATRIX.keys())
RELEASES = list(REVERSED_MATRIX.keys())
ALL_COMPONENTS = set([
    "all", "baremetal", "cinder", "clients", "cloudops",
    "common", "compute", "glance", "manila",
    "network", "octavia", "security", "swift",
    "tempest", "tripleo", "ui", "validation"])

INFLUX_PASSED = 9
INFLUX_PENDING = 5
INFLUX_FAILED = 0

PROMOTIONS_LIMIT = 1

UPSTREAM_API_URL = "https://trunk.rdoproject.org/api-{system}-{release}"
UPSTREAM_CRITERIA_URL = (
    "https://raw.githubusercontent.com/rdo-infra/rdo-jobs/master/"
    "criteria/{system}/{release}.yaml")

DOWNSTREAM_API_URL = (
    "https://osp-trunk.hosted.upshift.rdu2.redhat.com/api-{system}-{release}")
DOWNSTREAM_HOST_URL = (
    "https://osp-trunk.hosted.upshift.rdu2.redhat.com/{system}-{release}/")
DOWNSTREAM_CRITERIA_URL = (
    'https://sf.hosted.upshift.rdu2.redhat.com/images/conf_ruck_rover.yaml')

UPSTREAM_PROMOTE_NAME = "current-podified"
DOWNSTREAM_PROMOTE_NAME = "current-tripleo"
DOWNSTREAM_COMPONENT_NAME = "component-ci-testing"


def web_scrape(url):
    logging.debug("Fetching url: %s", url)
    try:
        response = requests.get(url, verify=CERT_PATH)
        response.raise_for_status()
    except (requests.exceptions.HTTPError,
            requests.exceptions.RequestException) as err:
        raise SystemExit(err)

    logging.debug("Fetched url: %s", url)
    return response.text


def job_dict(job, in_criteria, in_alt_criteria):
    if job and job.success is True:
        status = INFLUX_PASSED
    elif job and job.success is False:
        status = INFLUX_FAILED
    else:
        status = INFLUX_PENDING

    return {
        'job_name': job.job_id,
        'criteria': job.job_id in in_criteria,
        'alt_criteria': in_alt_criteria.get(job.job_id, []),
        'logs': job.url,
        'status': status,
        'timestamp': job.timestamp,
        'success': job.success
    }


def split_jobs(jobs):
    passed = {}
    failed = {}
    no_result = {}
    in_criteria = {}

    for job in jobs:
        if job['criteria'] is True:
            in_criteria[job['job_name']] = job

        if job['status'] == INFLUX_PASSED:
            passed[job['job_name']] = job

        elif job['status'] == INFLUX_FAILED:
            failed[job['job_name']] = job

        elif job['status'] == INFLUX_PENDING:
            no_result[job['job_name']] = job

    to_promote = set(in_criteria).difference(passed)
    for job_to_promote in set(to_promote):
        alt_criteria = in_criteria[job_to_promote]['alt_criteria']
        alt_criteria_passed = set(alt_criteria).intersection(passed)

        if alt_criteria_passed:
            to_promote.remove(job_to_promote)
            in_criteria[job_to_promote]['success'] = True

    return (list(passed.values()), list(failed.values()),
            list(no_result.values()), list(in_criteria.values()))


def get_dlrn_results(api_response, in_criteria, in_alt_criteria):
    """DLRN tests results.

    DLRN stores tests results in its internal DB.
    We use it to inform applications about current state of promotions.
    The only important information to us is latest successful test result
    from select api_response.

        :param api_response (object): Response from API.
        :return jobs (dict of dicts): It contains all last jobs from
            response with their appropriate status, timestamp and URL to
            test result.
    """
    logging.debug("Fetching DLRN results")
    jobs = {}

    for job in api_response:
        if not job.job_id.startswith(("periodic", "pipeline_")):
            # NOTE: Use only periodic jobs and pipeline_ (downstream jenkins)
            logging.debug("Skipping %s", job.job_id)
            continue

        existing_job = jobs.get(job.job_id)
        if not existing_job:
            logging.debug("Adding %s: %d", job.job_id, job.timestamp)
            jobs[job.job_id] = job_dict(job, in_criteria, in_alt_criteria)
            continue

        if job.timestamp > existing_job['timestamp']:
            if existing_job['success'] and not job.success:
                continue

            # NOTE(dasm): Overwrite *only* when recent job succeeded.
            logging.debug("Updating %s: %d", job.job_id, job.timestamp)
            jobs[job.job_id] = job_dict(job, in_criteria, in_alt_criteria)

    logging.debug("Fetched DLRN jobs")
    return list(jobs.values())


def fetch_component(api_instance, component_name, jobs_in_criteria):
    logging.debug("Fetching component pipeline: %s - %s",
                  DOWNSTREAM_COMPONENT_NAME, component_name)
    params = dlrnapi_client.PromotionQuery(
        promote_name=DOWNSTREAM_COMPONENT_NAME,
        component=component_name,
        limit=PROMOTIONS_LIMIT
    )
    promotions = api_instance.api_promotions_get(params)

    results = []
    for promotion in promotions:
        params = dlrnapi_client.Params2(
            commit_hash=promotion.commit_hash,
            distro_hash=promotion.distro_hash,
            extended_hash=promotion.extended_hash
        )
        aggregate = api_instance.api_repo_status_get(params)
        jobs_list = get_dlrn_results(aggregate, jobs_in_criteria, {})
        passed, failed, no_result, in_criteria = split_jobs(jobs_list)

        results.append({
            "promotion_date": promotion.timestamp,
            "passed": passed,
            "failed": failed,
            "no_result": no_result,
            "in_criteria": in_criteria,
            "aggregate_hash": promotion.aggregate_hash,
        })
    return results


def fetch_integration(
        api_instance, promote_name, jobs_in_criteria, jobs_alt_criteria):
    logging.debug("Fetching integrations for %s", promote_name)
    params = dlrnapi_client.PromotionQuery(
        promote_name=promote_name,
        limit=PROMOTIONS_LIMIT
    )
    promotions = api_instance.api_promotions_get(params)

    results = []
    for promotion in promotions:
        params = dlrnapi_client.AggQuery(
            aggregate_hash=promotion.aggregate_hash
        )
        aggregate = api_instance.api_agg_status_get(params)
        jobs_list = get_dlrn_results(
            aggregate, jobs_in_criteria, jobs_alt_criteria)
        passed, failed, no_result, in_criteria = split_jobs(jobs_list)

        results.append({
            "promotion_date": promotion.timestamp,
            "passed": passed,
            "failed": failed,
            "no_result": no_result,
            "in_criteria": in_criteria,
            "aggregate_hash": promotion.aggregate_hash,
        })
    return results


def downstream_component(system, release, component_name):
    config = yaml.safe_load(web_scrape(DOWNSTREAM_CRITERIA_URL))

    logging.debug("Configure DLRN API for downstream")
    dlrnapi_client.configuration.ssl_ca_cert = CERT_PATH
    dlrnapi_client.configuration.server_principal = (
        config['downstream']['dlrnapi_krb_principal'])

    url = config['downstream']['criteria'][system][release]['comp_url']
    logging.debug("Downstream Integration URL: %s", url)
    criteria = yaml.safe_load(web_scrape(url))

    api_client = dlrnapi_client.ApiClient(
        criteria['api_url'], auth_method="kerberosAuth", force_auth=True)
    api_instance = dlrnapi_client.DefaultApi(api_client)

    jobs_in_criteria = set(criteria['promoted-components'].get(
        component_name, []))

    return fetch_component(api_instance, component_name, jobs_in_criteria)


def downstream_integration(system, release):
    config = yaml.safe_load(web_scrape(DOWNSTREAM_CRITERIA_URL))

    logging.debug("Configure DLRN API for downstream")
    dlrnapi_client.configuration.ssl_ca_cert = CERT_PATH
    dlrnapi_client.configuration.server_principal = (
        config['downstream']['dlrnapi_krb_principal'])

    url = config['downstream']['criteria'][system][release]['int_url']
    logging.debug("Downstream Integration URL: %s", url)
    criteria = yaml.safe_load(web_scrape(url))

    jobs_in_criteria = set(
        criteria['promotions'][DOWNSTREAM_PROMOTE_NAME]['criteria'])
    logging.debug("Downstream jobs in criteria: %s", jobs_in_criteria)
    jobs_alt_criteria = (
        criteria['promotions'][DOWNSTREAM_PROMOTE_NAME].get(
            'alternative_criteria', {}))
    logging.debug("Downstream jobs in alternative criteria: %s",
                  jobs_alt_criteria)

    logging.debug("Configure DLRN API client")
    api_client = dlrnapi_client.ApiClient(
        criteria['api_url'], auth_method="kerberosAuth", force_auth=True)
    api_instance = dlrnapi_client.DefaultApi(api_client)

    return fetch_integration(
            api_instance,
            DOWNSTREAM_PROMOTE_NAME,
            jobs_in_criteria,
            jobs_alt_criteria
    )


def upstream_integration(release, system):
    url = UPSTREAM_CRITERIA_URL.format(system=system, release=release)
    config = yaml.safe_load(web_scrape(url))
    jobs_in_criteria = config[UPSTREAM_PROMOTE_NAME]

    host = UPSTREAM_API_URL.format(system=system, release=release)
    api_client = dlrnapi_client.ApiClient(host)
    api_instance = dlrnapi_client.DefaultApi(api_client)

    return fetch_integration(
        api_instance,
        UPSTREAM_PROMOTE_NAME,
        jobs_in_criteria,
        {}
    )


def upstream(release, system, component=None):
    results = upstream_integration(release, system)
    return results


def downstream(release, system, component=None):
    if component:
        results = downstream_component(system, release, component)
    else:
        results = downstream_integration(system, release)
    return results


STREAM = {
    "centos9": upstream,
    "rhel8": downstream,
    "rhel9": downstream,
    "rhel-8": downstream,
    "rhel-9": downstream,
}


@app.errorhandler(404)
def internal_error(error):
    data = {"error": error.description}
    return jsonify(data), error.code


@app.route("/<system>/<release>/<component>")
@app.route("/<system>/<release>/")
@app.route("/<system>/<release>")
def run(system, release, component=None):
    try:
        systems = REVERSED_MATRIX[release]
    except KeyError:
        abort(404, f"wrong release: {release}")

    try:
        releases = MATRIX[system]
    except KeyError:
        abort(404, f"wrong system: {system}")

    if system not in systems or release not in releases:
        msg = f'release {release} is not supported for {system}.'
        abort(404, msg)

    # TODO(dasm): Ensure that we're protected from providing component
    # to non-component releases
    stream = STREAM[system]
    data = stream(release, system, component)
    return jsonify(data), 200
