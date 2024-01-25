#!/usr/bin/env python

import json
import logging
import os
from datetime import datetime

import click
import dlrnapi_client
import requests
import yaml
from click.exceptions import BadParameter
from jinja2 import Environment, FileSystemLoader
from rich.console import Console
from rich.table import Table

console = Console()

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


def sort_jobs(jobs):
    passed = {}
    failed = {}
    no_result = {}
    in_criteria = {}
    failed_urls = set()

    for job in jobs:
        if job['criteria'] is True:
            in_criteria[job['job_name']] = job

        if job['status'] == INFLUX_PASSED:
            passed[job['job_name']] = job

        elif job['status'] == INFLUX_FAILED:
            failed[job['job_name']] = job
            failed_urls.add(job['logs'])

        elif job['status'] == INFLUX_PENDING:
            no_result[job['job_name']] = job

    to_promote = set(in_criteria).difference(passed)
    for job_to_promote in set(to_promote):
        alt_criteria = in_criteria[job_to_promote]['alt_criteria']
        alt_criteria_passed = set(alt_criteria).intersection(passed)

        if alt_criteria_passed:
            to_promote.remove(job_to_promote)
            in_criteria[job_to_promote]['success'] = True

    return passed, failed, no_result, in_criteria


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


def print_a_set_in_table(jobs, header="Job name"):
    if not jobs:
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column(header, style="dim", width=80)
    for job in sorted(jobs):
        table.add_row(job)
    console.print(table)


def prepare_render_template(filename):
    path = os.path.dirname(__file__)
    file_loader = FileSystemLoader(path + '/templates')
    env = Environment(loader=file_loader)
    template = env.get_template(filename)
    return template


def render_integration_yaml(jobs, test_hash):
    template = prepare_render_template('integration.yaml.j2')
    output = template.render(jobs=jobs, hash=test_hash)
    print(output)


def render_component_yaml(jobs):
    template = prepare_render_template('component.yaml.j2')
    output = template.render(jobs=jobs)
    print(output)


def render_tables(passed, failed, no_result, in_criteria, timestamp,
                  component, test_hash):
    """
    jobs_to_promote are any job that hasn't registered
    success w/ dlrn. jobs_pending are any jobs in pending.
    We only want test project config for jobs that have completed.
    execute if there are failing jobs in criteria and if
    you are only looking at one component and not all components
    """

    to_promote = set(in_criteria).difference(passed)
    if failed:
        status = "Red"
    elif not to_promote:
        status = "Green"
    else:
        status = "Yellow"

    component_ui = f"{component} component" if component else ""
    status_ui = f"status={status}"
    promotion_ui = f"last_promotion={timestamp}"
    header_ui = " ".join([component_ui, status_ui, promotion_ui])

    console.print(header_ui)

    print_a_set_in_table(passed, "Jobs which passed:")
    print_a_set_in_table(failed, "Jobs which failed:")
    print_a_set_in_table(no_result, "Pending running jobs")

    if failed:
        console.print("Logs of failing jobs:")
        for value in failed.values():
            console.print(value['logs'])

    # NOTE: Print new line to separate results
    console.print("\n")

    to_promote_jobs = to_promote - set(no_result)
    if to_promote_jobs:
        if component:
            render_component_yaml(to_promote_jobs)
        else:
            render_integration_yaml(to_promote_jobs, test_hash)


def render_tables_proxy(results, component=None):
    for result in results:
        timestamp = datetime.utcfromtimestamp(result['promotion_date'])

        passed = result['passed']
        failed = result['failed']
        no_result = result['no_result']
        in_criteria = result['in_criteria']
        promotion_hash = result['aggregate_hash']

        render_tables(passed, failed, no_result, in_criteria, timestamp,
                      component, promotion_hash)


def component_function(api_instance, component_name, jobs_in_criteria):
    logging.debug("Fetching component pipeline")
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
        passed, failed, no_result, in_criteria = sort_jobs(jobs_list)

        results.append({
            "promotion_date": promotion.timestamp,
            "passed": passed,
            "failed": failed,
            "no_result": no_result,
            "in_criteria": in_criteria,
            "aggregate_hash": promotion.aggregate_hash,
        })
    return results


def integration_function(
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
        passed, failed, no_result, in_criteria = sort_jobs(jobs_list)

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

    return component_function(
        api_instance, component_name, jobs_in_criteria)


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

    return integration_function(
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

    return integration_function(
        api_instance,
        UPSTREAM_PROMOTE_NAME,
        jobs_in_criteria,
        {}
    )


def upstream(release, system, *_args, **_kwargs):
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


@click.option("--jsonize", is_flag=True, default=False)
@click.option("--verbose", is_flag=True, default=False)
@click.option("--component", default=None,
              type=click.Choice(sorted(ALL_COMPONENTS)))
@click.option("--distro", default=DISTROS[0], type=click.Choice(DISTROS))
@click.option("--release", default=RELEASES[0], type=click.Choice(RELEASES))
@click.command()
def main(release, distro, component, verbose, jsonize):
    if verbose:
        fmt = '%(asctime)s:%(levelname)s - %(funcName)s:%(lineno)s %(message)s'
        logging.basicConfig(format=fmt, encoding='utf-8', level=logging.DEBUG)

    distros = REVERSED_MATRIX[release]
    releases = MATRIX[distro]
    if distro not in distros or release not in releases:
        msg = f'Release {release} is not supported for {distro}.'
        raise BadParameter(msg)
    logging.info("Starting script: %s - %s", distro, release)

    # NOTE (dasm): Dynamically select up/downstream function based on distro
    stream = STREAM[distro]
    results = stream(release, distro, component)
    if jsonize:
        print(json.dumps(results))
    else:
        render_tables_proxy(results, component)


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter
