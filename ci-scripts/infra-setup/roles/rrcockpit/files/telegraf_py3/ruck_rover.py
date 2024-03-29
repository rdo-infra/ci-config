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
from dlrnapi_client.rest import ApiException
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

ZUUL_JOBS_LIMIT = 1000
ZUUL_JOB_HISTORY_THRESHOLD = 5

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


class AttributeDict(dict):
    def __getattr__(self, name):
        return (self[name] if not isinstance(self[name], dict)
                else AttributeDict(self[name]))


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


def url_response_in_yaml(url):
    logging.debug("Fetching URL: %s", url)
    text_response = web_scrape(url)
    processed_data = yaml.safe_load(text_response)

    logging.debug("Return processed data")
    return processed_data


def fetch_hashes_from_commit_yaml(criteria):
    """
    This function finds commit hash, distro hash, extended_hash from commit.yaml
    :param url for commit.yaml
    :returns values for commit_hash, distro_hash, extended_hash
    """
    commit_hash = criteria['commits'][0]['commit_hash']
    distro_hash = criteria['commits'][0]['distro_hash']
    extended_hash = criteria['commits'][0]['extended_hash']
    if extended_hash == "None":
        extended_hash = None

    return commit_hash, distro_hash, extended_hash


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


def get_dlrn_promotions(api_url, promotion_name, component=None):
    """
    This function gets latest promotion line details [1][2].

    Example response:

    'aggregate_hash': '07de61e27b4e499da58b393bb5e98313',
    'commit_hash': '4d8e55c5fe0cddaa62008c105d37c5349323f366',
    'component': 'common',
    'distro_hash': 'bb0ff4fd97cda359c6947e38a54a7fa5b16d0176',
    'extended_hash': None,
    'promote_name': 'current-tripleo',
    'repo_hash': '4d8e55c5fe0cddaa62008c105d37c5349323f366_bb0ff4fd',
    'repo_url': 'https://trunk.rdoproject.org/centos9-master/component
    /common/4d/8e/4d8e55c5fe0cddaa62008c105d37c5349323f366_bb0ff4fd',
    'timestamp': 1650363176,
    'user': 'ciuser'

    :param api_url (str): The DLRN API endpoint for the release.
    :param promotion_name (str): Promotion name for a line.
    :param component (str) [optional]: Component to be fetched.
    :return pr (object): Response from API.

    [1]: https://github.com/softwarefactory-project/dlrnapi_client/
         blob/master/docs/DefaultApi.md#api_promotions_get
    [2]: https://dlrn.readthedocs.io/en/latest/api.html#get-api-promotions
    """
    logging.debug("Getting promotion %s for %s", promotion_name, api_url)
    api_client = dlrnapi_client.ApiClient(host=api_url,
                                          auth_method="kerberosAuth",
                                          force_auth=True)
    api_instance = dlrnapi_client.DefaultApi(api_client)
    query = dlrnapi_client.PromotionQuery(
        promote_name=promotion_name,
        component=component,
        limit=1
    )
    pr = api_instance.api_promotions_get(query)
    return pr[0]


def find_results_from_dlrn_repo_status(api_url, commit_hash,
                                       distro_hash, extended_hash):
    """ This function returns api_response from dlrn for a particular
        commit_hash, distro_hash, extended_hash.
        https://github.com/softwarefactory-project/dlrnapi_client/blob/master/
        docs/DefaultApi.md#api_repo_status_get

        :param api_url: the dlrn api endpoint for a particular release
        :param commit_hash: For a particular repo, commit.yaml contains this
         info.
        :param distro_hash: For a particular repo, commit.yaml contains this
         info.
        :param extended_hash: For a particular repo, commit.yaml contains this
         info.
        :return api_response: from dlrnapi server containing result of
         passing/failing jobs
    """
    api_client = dlrnapi_client.ApiClient(host=api_url,
                                          auth_method="kerberosAuth",
                                          force_auth=True)
    api_instance = dlrnapi_client.DefaultApi(api_client)
    params = dlrnapi_client.Params2(commit_hash=commit_hash,
                                    distro_hash=distro_hash,
                                    extended_hash=extended_hash)
    try:
        api_response = api_instance.api_repo_status_get(params=params)
    except ApiException as err:
        print("Exception when calling DefaultApi->api_repo_status_get:"
              " %s\n" % err)
    return api_response


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


def get_job_history(jobs, url):
    """Fetch jobs history from provided URL.

    :param jobs (set): Set of job names
    :param url (str): URL to fetch job history from.
    :return history (dict): Summary of history for all jobs.
    """
    if not jobs:
        return {}

    if not url:
        return {}

    logging.debug("Fetching jobs history")
    response = requests.get(
        url,
        params={
            'job_name': jobs,
            'limit': ZUUL_JOBS_LIMIT,
        },
        headers={'Accept': 'application/json'},
        verify=CERT_PATH
    )
    logging.debug(response.url)

    history = {}
    for job in response.json():
        job_name = job['job_name']
        result = job['result']

        job_history = history.setdefault(
            job_name, {'SUCCESS': 0, 'FAILURE': 0, 'OTHER': 0})

        if (job_history['SUCCESS'] + job_history['FAILURE']
                + job_history['OTHER']) >= ZUUL_JOB_HISTORY_THRESHOLD:
            continue

        if result in ("SUCCESS", 'FAILURE'):
            job_history[result] += 1
        else:
            job_history['OTHER'] += 1

    logging.debug("Return jobs history")
    return history


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


def print_failed_in_criteria(jobs):
    """Print jobs history.

    : param jobs (dict): History of jobs running midstream.
    : return None
    """

    if not jobs:
        return

    header = "Jobs in promotion criteria required to promo the hash: "
    table = Table(show_header=True, header_style="bold")
    table.add_column(header, width=80)
    table.add_column("Pass", width=15)
    table.add_column("Failure", width=15)
    table.add_column("Others", width=15)

    for job_name, job_stats in sorted(jobs.items()):
        table.add_row(
            job_name,
            str(job_stats['SUCCESS']),
            str(job_stats['FAILURE']),
            str(job_stats['OTHER']),
        )
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


def render_integration_yaml(jobs, test_hash, testproject_url):
    template = prepare_render_template('integration.yaml.j2')
    output = template.render(
        jobs=jobs, hash=test_hash, testproject_url=testproject_url)
    print(output)


def render_component_yaml(jobs, testproject_url):
    template = prepare_render_template('component.yaml.j2')
    output = template.render(
        jobs=jobs, testproject_url=testproject_url)
    print(output)


def render_tables(jobs, timestamp, under_test_url, component,
                  components, api_response, pkg_diff, test_hash,
                  periodic_builds_url, testproject_url):
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
    hash_ui = f"Hash_under_test={under_test_url}"
    header_ui = " ".join([component_ui, status_ui, promotion_ui])

    console.print(header_ui)
    console.print(hash_ui)

    print_a_set_in_table(passed, "Jobs which passed:")
    print_a_set_in_table(failed, "Jobs which failed:")
    print_a_set_in_table(no_result, "Pending running jobs")

    periodic_history = get_job_history(to_promote, periodic_builds_url)

    print_failed_in_criteria(periodic_history)

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
        if len(components) != 0 and components[0] is not None:
            render_component_yaml(tp_jobs, testproject_url)
        else:
            render_integration_yaml(tp_jobs, test_hash, testproject_url)


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


def track_component_promotion(
        api_url, base_url, criteria, periodic_builds_url, testproject_url,
        promotion_name, aggregate_hash, test_component):
    logging.debug("Starting component track")

    components, pkg_diff = get_package_diff(
        base_url, test_component, promotion_name, aggregate_hash)

    for component in components:
        logging.debug("Fetching component: %s data", component)

        component_url = COMPONENT_COMMIT_URL.format(
            url=base_url, component=component)
        component_criteria = url_response_in_yaml(component_url)

        commit_hash, distro_hash, extended_hash = fetch_hashes_from_commit_yaml(
            component_criteria)
        api_response = find_results_from_dlrn_repo_status(
            api_url, commit_hash, distro_hash, extended_hash)

        promotion = get_dlrn_promotions(
            api_url, "promoted-components", component)
        timestamp = datetime.utcfromtimestamp(promotion.timestamp)

        test_hash = commit_hash
        under_test_url = COMPONENT_TEST_URL.format(
            url=api_url, commit_hash=commit_hash, distro_hash=distro_hash)

        jobs_in_criteria = set(criteria['promoted-components'].get(
            component, []))

        dlrn_jobs = get_dlrn_results(api_response)
        jobs = prepare_jobs(jobs_in_criteria, {}, dlrn_jobs)

        render_tables(
            jobs, timestamp, under_test_url, component,
            components, api_response, pkg_diff, test_hash,
            periodic_builds_url, testproject_url)
        logging.debug("Finished component: %s data", component)

    logging.debug("Finshed component track")


def render_tables_proxy(results, pkg_diff=None):
    for timestamp, result in results.items():
        timestamp = datetime.utcfromtimestamp(timestamp)

        jobs = result['jobs']
        aggregate = result['aggregate']
        promotion_hash = result['aggregate_hash']

        render_tables(jobs, timestamp, promotion_hash, None, [], aggregate,
                      pkg_diff, promotion_hash, "", "")


def integration(api_instance, promote_name, jobs_in_criteria,
                jobs_alt_criteria):
    logging.debug("Fetching integrations for %s", promote_name)
    params = dlrnapi_client.PromotionQuery(
        promote_name=promote_name, limit=PROMOTIONS_LIMIT)
    promotions = api_instance.api_promotions_get(params)

    results = {}
    for promotion in promotions:
        params = dlrnapi_client.AggQuery(
            aggregate_hash=promotion.aggregate_hash)
        aggregate = api_instance.api_agg_status_get(params)

        dlrn_jobs = get_dlrn_results(aggregate)
        jobs = prepare_jobs(jobs_in_criteria, jobs_alt_criteria, dlrn_jobs)

        results[promotion.timestamp] = {
            "jobs": jobs,
            "aggregate": aggregate,
            "aggregate_hash": promotion.aggregate_hash,
        }
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


def upstream_proxy(release, system, *_args, **_kwargs):
    url = UPSTREAM_CRITERIA_URL.format(system=system, release=release)
    config = yaml.safe_load(web_scrape(url))
    jobs_in_criteria = config[UPSTREAM_PROMOTE_NAME]

    host = UPSTREAM_API_URL.format(system=system, release=release)
    api_client = dlrnapi_client.ApiClient(host)
    api_instance = dlrnapi_client.DefaultApi(api_client)

    results = integration(
        api_instance,
        UPSTREAM_PROMOTE_NAME,
        jobs_in_criteria,
        {}
    )
    render_tables_proxy(results)


def downstream(release, distro, promotion_name, aggregate_hash, component):
    config = yaml.safe_load(web_scrape(DOWNSTREAM_CRITERIA_URL))
    krb_principal = config['downstream']['dlrnapi_krb_principal']

    dlrnapi_client.configuration.ssl_ca_cert = CERT_PATH
    dlrnapi_client.configuration.server_principal = krb_principal

    periodic_builds_url = config['downstream']['periodic_builds_url']
    testproject_url = config['downstream']['testproject_url']

    if component:
        url = config['downstream']['criteria'][distro][release]['comp_url']
        criteria = url_response_in_yaml(url)
        criteria = AttributeDict(criteria)

        promotion_name = "current-tripleo"
        aggregate_hash = "component-ci-testing"

        track_component_promotion(
            criteria.api_url, criteria.base_url, criteria, periodic_builds_url,
            testproject_url, promotion_name, aggregate_hash, component)
    elif not component:
        # NOTE(dasm): pkg_diff is currently being used by integration downstream
        # NOTE(dasm): It is a temporary workaround
        # TODO(dasm): Change the way how packages are compared
        url = config['downstream']['criteria'][distro][release]['int_url']
        criteria = url_response_in_yaml(url)
        _, pkg_diff = get_package_diff(
            criteria['base_url'], None,
            DOWNSTREAM_PROMOTE_NAME, DOWNSTREAM_TESTING_NAME)
        results = downstream_integration(distro, release)
        render_tables_proxy(results, pkg_diff)
    else:
        raise Exception("Unsupported")
    logging.info("Finished script: %s - %s", distro, release)


STREAM = {
    "centos9": upstream_proxy,
    "rhel8": downstream,
    "rhel9": downstream,
    "rhel-8": downstream,
    "rhel-9": downstream,
}


@click.option("--verbose", is_flag=True, default=False)
@click.option("--component", default=None,
              type=click.Choice(sorted(ALL_COMPONENTS)))
@click.option("--aggregate_hash", default="tripleo-ci-testing",
              # TO-DO w/ tripleo-get-hash
              help=("default:tripleo-ci-testing"
                    "\nexample:tripleo-ci-testing/e6/ad/e6ad..."))
@click.option("--promotion_name", default="current-tripleo",
              type=click.Choice(["current-tripleo", "current-tripleo-rdo",
                                 "current-podified"]))
@click.option("--distro", default=DISTROS[0], type=click.Choice(DISTROS))
@click.option("--release", default=RELEASES[0], type=click.Choice(RELEASES))
@click.command()
def main(release, distro, promotion_name, aggregate_hash, component, verbose):
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
    stream(release, distro, promotion_name, aggregate_hash, component)


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter
