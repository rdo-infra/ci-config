#!/usr/bin/env python

import csv
import logging
import os
import time
from datetime import datetime
from io import StringIO

import click
import dlrnapi_client
import requests
import yaml
from click.exceptions import BadParameter
from jinja2 import Environment, FileSystemLoader
from rich import print as rich_print
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

INTEGRATION_COMMIT_URL = "{url}/{aggregate_hash}/delorean.repo.md5"
INTEGRATION_TEST_URL = "{url}/api/civotes_agg_detail.html?ref_hash={ref_hash}"
INTEGRATION_DLRN_VERSIONS_CSV = "{url}/{tag}/versions.csv"

COMPONENT_COMMIT_URL = ("{url}/component/{component}/component-ci-testing/"
                        "commit.yaml")
COMPONENT_TEST_URL = ("{url}/api/civotes_detail.html?"
                      "commit_hash={commit_hash}&distro_hash={distro_hash}")
COMPONENT_DLRN_VERSIONS_CSV = "{url}/component/{component}/{tag}/versions.csv"

UPSTREAM_PROMOTE_NAME = "current-podified"
DOWNSTREAM_PROMOTE_NAME = "current-tripleo"
DOWNSTREAM_TESTING_NAME = "tripleo-ci-testing"
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


def get_csv(url):
    logging.debug("Fetching CSV from %s", url)
    response = requests.get(url, verify=CERT_PATH)
    if response.ok:
        content = response.content.decode('utf-8')
        f = StringIO(content)
        reader = csv.reader(f, delimiter=',')
        logging.debug("Fetched CSV from %s", url)
        return [content, reader]


def get_diff(control_tag, file1, test_tag, file2):
    # compare the raw string
    if file1[0] == file2[0]:
        return False
    else:
        # for the line by line diff, use csv content
        table = Table(show_header=True, header_style="bold")
        table.add_column(control_tag, style="dim", width=85)
        table.add_column(test_tag, style="dim", width=85)
        logging.debug("Compare files")
        for f1, f2 in zip(file1[1], file2[1]):
            if f1 != f2:
                table.add_row(str(f1[9]), str(f2[9]))
        logging.debug("Files compared")
        return table


def get_dlrn_results(api_response):
    """DLRN tests results.

    DLRN stores tests results in its internal DB.
    We use it to inform applications about current state of promotions.
    The only important information to us is latest successful test result
    from select api_response.

        :param api_response (object): Response from API.
        :return jobs (dict of objects): It contains all last jobs from
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
            jobs[job.job_id] = job
            logging.debug("Adding %s: %d", job.job_id, job.timestamp)
            continue

        if job.timestamp > existing_job.timestamp:
            if existing_job.success and not job.success:
                continue

            # NOTE(dasm): Overwrite *only* when recent job succeeded.
            logging.debug("Updating %s: %d", job.job_id, job.timestamp)
            jobs[job.job_id] = job

    logging.debug("Fetched DLRN jobs")
    return jobs


def latest_job_results_url(api_response, all_jobs):
    logging.debug("Get latest job url")
    logs_job = {}
    for particular_job in all_jobs:
        latest_log = {}
        for job in api_response:
            if job.job_id == particular_job:
                latest_log[job.timestamp] = job.url
        logs_job[particular_job] = latest_log[max(latest_log.keys())]

    logging.debug("Return latest jobs: %s", logs_job)
    return logs_job


def print_a_set_in_table(jobs, header="Job name"):
    if not jobs:
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column(header, style="dim", width=80)
    for job in sorted(jobs):
        table.add_row(job)
    console.print(table)


def prepare_jobs(jobs_in_criteria, jobs_in_alt_criteria, dlrn_jobs):
    """
    InfluxDB follows line protocol [1]

    Syntax:
    "jobs_result" and "dlrn-promotion" are 'measurement',
    which describes a "bucket" where data is stored.
    Next are optional 'tags', represented as key-value pairs.
    Whitespace divides above from fields.
    All field key-value pairs are separated by commas.
    Whitespace separates fields from optional timestamp.
    <measurement>[,<tag_key>=<tag_value>] <field_key>=<field_value>[
                                       ,<field_key>=<field_value>] [<timestamp>]

    [1] https://docs.influxdata.com/influxdb/v2.0/reference/syntax/line-protocol

    Grafana
    It stores colors as numbers, not text:
    * 0 - failed
    * 5 - pending
    * 9 - success

    Epoch is rendered only with *1000

    :param jobs_in_criteria (set): Jobs which are required for promotion.
    :param jobs_in_alt_criteria (set): Jobs which can be switched for promotion.
    :param dlrn_jobs (dict of objects): Jobs, registered by DLRN.
    :return job_result_list (list of dicts): List of parsed jobs.
    """

    logging.debug("Preparing jobs info")

    all_jobs = set(dlrn_jobs).union(jobs_in_criteria)

    zuul_jobs = {}
    logging.debug("Parsing jobs")
    job_result_list = []
    for job_name in sorted(all_jobs):
        job = dlrn_jobs.get(job_name)
        if job and job.success is True:
            status = INFLUX_PASSED
        elif job and job.success is False:
            status = INFLUX_FAILED
        else:
            status = INFLUX_PENDING

        # NOTE(dasm): DLRN returns job.url without trailing '/'
        log_url = job.url + '/' if job else "N/A"
        zuul_job = zuul_jobs.get(log_url)
        if not zuul_job:
            logging.info("Missing job %s", log_url)
            zuul_job = {}

        d = zuul_job.get('duration', 0)
        duration = time.strftime("%H hr %M mins %S secs", time.gmtime(d))
        job_result = {
            'job_name': job_name,
            'criteria': job_name in jobs_in_criteria,
            'alt_criteria': jobs_in_alt_criteria.get(job_name, []),
            'logs': log_url,
            'duration': duration,
            'status': status,
        }
        job_result_list.append(job_result)
    logging.debug("Prepared jobs info: %s", job_result_list)

    return job_result_list


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


def render_tables(jobs, timestamp, component, api_response, pkg_diff,
                  test_hash):
    """
    jobs_to_promote are any job that hasn't registered
    success w/ dlrn. jobs_pending are any jobs in pending.
    We only want test project config for jobs that have completed.
    execute if there are failing jobs in criteria and if
    you are only looking at one component and not all components
    """

    passed = set(k['job_name'] for k in jobs if k['status'] == INFLUX_PASSED)
    failed = set(k['job_name'] for k in jobs if k['status'] == INFLUX_FAILED)
    no_result = set(
        k['job_name'] for k in jobs if k['status'] == INFLUX_PENDING)
    in_criteria_dict = {
        k['job_name']: k['alt_criteria'] for k in jobs if k['criteria'] is True
    }
    in_criteria = set(in_criteria_dict)
    to_promote = in_criteria.difference(passed)

    for job_to_promote in set(to_promote):
        alt_criteria = in_criteria_dict[job_to_promote]
        alt_criteria_passed = set(alt_criteria).intersection(passed)

        if alt_criteria_passed:
            to_promote.remove(job_to_promote)
            in_criteria.update(alt_criteria_passed)

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

    log_urls = latest_job_results_url(api_response, failed)
    if log_urls:
        console.print("Logs of failing jobs:")
    for value in log_urls.values():
        console.print(value)

    if pkg_diff:
        console.print("\n Packages Tested")
        rich_print(pkg_diff)

    # NOTE: Print new line to separate results
    console.print("\n")

    tp_jobs = to_promote - no_result
    if tp_jobs:
        if component:
            render_component_yaml(tp_jobs)
        else:
            render_integration_yaml(tp_jobs, test_hash)


def get_package_diff(base_url, component, promotion_name, aggregate_hash):
    logging.debug("Get diff of tested packages")

    if component == "all":
        logging.debug("Skip checking packages diff")
        components = sorted(ALL_COMPONENTS.difference(["all"]))
        return components, None

    elif not component:
        logging.debug("Integration diff URL")
        control_url = INTEGRATION_DLRN_VERSIONS_CSV.format(
            url=base_url, tag=promotion_name)
        test_url = INTEGRATION_DLRN_VERSIONS_CSV.format(
            url=base_url, tag=aggregate_hash)

    elif component and component != "all":
        logging.debug("Component diff URL for %s", component)
        control_url = COMPONENT_DLRN_VERSIONS_CSV.format(
            url=base_url, component=component, tag=promotion_name)
        test_url = COMPONENT_DLRN_VERSIONS_CSV.format(
            url=base_url, component=component, tag=aggregate_hash)

    control_csv = get_csv(control_url)
    test_csv = get_csv(test_url)

    components = [component]
    diff = get_diff(promotion_name, control_csv, aggregate_hash, test_csv)
    return components, diff


def render_tables_proxy(results, pkg_diff=None, component=None):
    for timestamp, result in results.items():
        timestamp = datetime.utcfromtimestamp(timestamp)

        jobs = result['jobs']
        aggregate = result['aggregate']
        promotion_hash = result['aggregate_hash']

        render_tables(jobs, timestamp, component, aggregate, pkg_diff,
                      promotion_hash)


def component(api_instance, component_name, jobs_in_criteria):
    logging.debug("Fetching component pipeline")
    params = dlrnapi_client.PromotionQuery(
        promote_name=DOWNSTREAM_COMPONENT_NAME,
        component=component_name,
        limit=PROMOTIONS_LIMIT
    )
    promotions = api_instance.api_promotions_get(params)

    results = {}
    for promotion in promotions:
        params = dlrnapi_client.Params2(
            commit_hash=promotion.commit_hash,
            distro_hash=promotion.distro_hash,
            extended_hash=promotion.extended_hash
        )
        aggregate = api_instance.api_repo_status_get(params)

        dlrn_jobs = get_dlrn_results(aggregate)
        jobs = prepare_jobs(jobs_in_criteria, {}, dlrn_jobs)

        results[promotion.timestamp] = {
            "jobs": jobs,
            "aggregate": aggregate,
            "aggregate_hash": promotion.aggregate_hash,
        }
    return results


def integration(api_instance, promote_name, jobs_in_criteria,
                jobs_alt_criteria):
    logging.debug("Fetching integrations for %s", promote_name)
    params = dlrnapi_client.PromotionQuery(
        promote_name=promote_name,
        limit=PROMOTIONS_LIMIT
    )
    promotions = api_instance.api_promotions_get(params)

    results = {}
    for promotion in promotions:
        params = dlrnapi_client.AggQuery(
            aggregate_hash=promotion.aggregate_hash
        )
        aggregate = api_instance.api_agg_status_get(params)

        dlrn_jobs = get_dlrn_results(aggregate)
        jobs = prepare_jobs(jobs_in_criteria, jobs_alt_criteria, dlrn_jobs)

        results[promotion.timestamp] = {
            "jobs": jobs,
            "aggregate": aggregate,
            "aggregate_hash": promotion.aggregate_hash,
        }
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

    results = component(api_instance, component_name, jobs_in_criteria)
    return results


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

    return integration(api_instance, DOWNSTREAM_PROMOTE_NAME,
                       jobs_in_criteria, jobs_alt_criteria)


def upstream_integration(release, system):
    url = UPSTREAM_CRITERIA_URL.format(system=system, release=release)
    config = yaml.safe_load(web_scrape(url))
    jobs_in_criteria = config[UPSTREAM_PROMOTE_NAME]

    host = UPSTREAM_API_URL.format(system=system, release=release)
    api_client = dlrnapi_client.ApiClient(host)
    api_instance = dlrnapi_client.DefaultApi(api_client)

    return integration(
        api_instance,
        UPSTREAM_PROMOTE_NAME,
        jobs_in_criteria,
        {}
    )


def upstream(release, system, *_args, **_kwargs):
    results = upstream_integration(release, system)
    render_tables_proxy(results)


def downstream(release, distro, component=None):
    config = yaml.safe_load(web_scrape(DOWNSTREAM_CRITERIA_URL))
    if component:
        url = config['downstream']['criteria'][distro][release]['comp_url']
        criteria = yaml.safe_load(web_scrape(url))
        _, pkg_diff = get_package_diff(
            criteria['base_url'],
            component,
            DOWNSTREAM_PROMOTE_NAME,
            DOWNSTREAM_COMPONENT_NAME
        )

        results = downstream_component(distro, release, component)
        render_tables_proxy(results, pkg_diff, component)

    elif not component:
        # NOTE(dasm): pkg_diff is currently being used by integration downstream
        # NOTE(dasm): It is a temporary workaround
        # TODO(dasm): Change the way how packages are compared
        url = config['downstream']['criteria'][distro][release]['int_url']
        criteria = yaml.safe_load(web_scrape(url))
        _, pkg_diff = get_package_diff(
            criteria['base_url'],
            None,
            DOWNSTREAM_PROMOTE_NAME,
            DOWNSTREAM_TESTING_NAME
        )

        results = downstream_integration(distro, release)
        render_tables_proxy(results, pkg_diff, component)
    else:
        raise Exception("Unsupported")
    logging.info("Finished script: %s - %s", distro, release)


STREAM = {
    "centos9": upstream,
    "rhel8": downstream,
    "rhel9": downstream,
    "rhel-8": downstream,
    "rhel-9": downstream,
}


@click.option("--verbose", is_flag=True, default=False)
@click.option("--component", default=None,
              type=click.Choice(sorted(ALL_COMPONENTS)))
@click.option("--distro", default=DISTROS[0], type=click.Choice(DISTROS))
@click.option("--release", default=RELEASES[0], type=click.Choice(RELEASES))
@click.command()
def main(release, distro, component, verbose):
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
    stream(release, distro, component)


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter
