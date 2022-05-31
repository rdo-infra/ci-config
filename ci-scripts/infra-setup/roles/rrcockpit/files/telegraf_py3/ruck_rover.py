#!/usr/bin/env python

import csv
import logging
import os
import re
import time
from datetime import datetime
from io import StringIO
from tempfile import mkstemp

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

# Use system-provided CA bundle instead of the one installed with pip
# in certifi.
CERT_PATH = '/etc/pki/ca-trust/extracted/openssl/ca-bundle.trust.crt'
dlrnapi_client.configuration.ssl_ca_cert = CERT_PATH

MATRIX = {
    "centos-8": ["wallaby", "victoria", "ussuri", "train"],
    "centos-9": ["master", "wallaby"],
    "rhel-8": ["osp17", "osp16-2"],
    "rhel-9": ["osp17"]
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

ZUUL_JOB_REGEX = re.compile(
    "periodic-(?P<job_name>.*)-(master|wallaby|victoria|ussuri|train)")


def download_file(url):
    logging.debug("Downloading URL: %s", url)
    response = requests.get(url, stream=True, verify=CERT_PATH)
    response.raise_for_status()
    file_descriptor, path = mkstemp(prefix="job-output-")
    with open(path, "wb") as file:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                file.write(chunk)
    os.close(file_descriptor)

    return path


def web_scrape(url):
    try:
        response = requests.get(url, verify=CERT_PATH)
        response.raise_for_status()
    except (requests.exceptions.HTTPError,
            requests.exceptions.RequestException) as err:
        raise SystemExit(err)

    return response.text


def url_response_in_yaml(url):
    logging.debug("Fetching URL: %s", url)
    text_response = web_scrape(url)
    processed_data = yaml.safe_load(text_response)

    logging.debug("Return processed data")
    return processed_data


def gather_basic_info_from_criteria(url):
    criteria_content = url_response_in_yaml(url)
    api_url = criteria_content['api_url']
    base_url = criteria_content['base_url']

    return api_url, base_url


def find_jobs_in_integration_criteria(url, promotion_name='current-tripleo'):
    criteria_content = url_response_in_yaml(url)

    return set(criteria_content['promotions'][promotion_name]['criteria'])


def find_jobs_in_component_criteria(url, component):
    criteria_content = url_response_in_yaml(url)

    return set(criteria_content['promoted-components'][component])


def fetch_hashes_from_commit_yaml(url):
    """
    This function finds commit hash, distro hash, extended_hash from commit.yaml
    :param url for commit.yaml
    :returns values for commit_hash, distro_hash, extended_hash
    """
    criteria_content = url_response_in_yaml(url)
    commit_hash = criteria_content['commits'][0]['commit_hash']
    distro_hash = criteria_content['commits'][0]['distro_hash']
    extended_hash = criteria_content['commits'][0]['extended_hash']
    if extended_hash == "None":
        extended_hash = None

    return commit_hash, distro_hash, extended_hash


def find_results_from_dlrn_agg(api_url, test_hash):
    api_client = dlrnapi_client.ApiClient(host=api_url)
    api_instance = dlrnapi_client.DefaultApi(api_client)
    params = dlrnapi_client.AggQuery(aggregate_hash=test_hash)
    api_response = api_instance.api_agg_status_get(params=params)

    return api_response


def format_ts_from_last_modified(ts, pattern='%a, %d %b %Y %H:%M:%S %Z'):
    ts = datetime.strptime(ts, pattern)
    return int(time.mktime(ts.timetuple()))


def get_last_modified_date(base_url, component=None):
    """Get the date of the consistent link in dlrn.
    """

    logging.debug("Get last modified date")
    repo = "delorean.repo"

    if component is None:
        # integration build, use last promoted_components date
        url = f'{base_url}promoted-components/{repo}'
    else:
        # TO-DO normalize component and intergration config
        url = f'{base_url}component/{component}/consistent/{repo}'

    response = requests.get(url, verify=CERT_PATH)
    if not response.ok:
        return None

    last_modified = response.headers['Last-Modified']
    consistent_date = format_ts_from_last_modified(last_modified)
    logging.debug("Last modified date: %s", last_modified)
    return consistent_date


def get_dlrn_versions_csv(base_url, component, tag):
    component_part = f"/component/{component}" if component else ""
    return f"{base_url}{component_part}/{tag}/versions.csv"


def get_csv(url):
    logging.debug("Fetching CSV from %s", url)
    response = requests.get(url, verify=CERT_PATH)
    if response.ok:
        content = response.content.decode('utf-8')
        f = StringIO(content)
        reader = csv.reader(f, delimiter=',')
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
        for f1, f2 in zip(file1[1], file2[1]):
            if f1 != f2:
                table.add_row(str(f1[9]), str(f2[9]))
        return table


def get_dlrn_promotions(api_url,
                        promotion_name,
                        component=None):
    """
    This function gets latest promotion line details [1].

    Example response:

    https://dlrn.readthedocs.io/en/latest/api.html#get-api-promotions
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
    """
    logging.debug("Getting promotion %s for %s", promotion_name, api_url)

    api_client = dlrnapi_client.ApiClient(host=api_url)
    api_instance = dlrnapi_client.DefaultApi(api_client)
    query = dlrnapi_client.PromotionQuery(limit=1,
                                          promote_name=promotion_name)
    if component:
        query.component = component
    pr = api_instance.api_promotions_get_with_http_info(query)[0][0]
    return pr


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
    api_client = dlrnapi_client.ApiClient(host=api_url)
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
        :return jobs (list of objects): It contains all last jobs from
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

    return jobs


def print_a_set_in_table(jobs, header="Job name"):
    if not jobs:
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column(header, style="dim", width=80)
    for job in jobs:
        table.add_row(job)
    console.print(table)


def print_failed_in_criteria(jobs, periodic_builds_url, upstream_builds_url):

    if not jobs:
        return

    header = "Jobs in promotion criteria required to promo the hash: "
    table = Table(show_header=True, header_style="bold")

    table.add_column(header, width=80)
    table.add_column("Integration PASSED History", width=15)
    table.add_column("Integration FAILURE History", width=15)
    table.add_column("Integration Other History", width=15)
    table.add_column("Upstream PASSED History", width=10)
    table.add_column("Upstream FAILURE History", width=10)
    table.add_column("Upstream Other History", width=10)

    rdo_history = query_zuul_job_history(jobs, url=periodic_builds_url)
    upstream_history = query_zuul_job_history(jobs, url=upstream_builds_url)

    for job in jobs:
        rdo_job = rdo_history.get(job, {})
        upstream_job = upstream_history.get(job, {})

        table.add_row(
            job,
            str(rdo_job.get("SUCCESS", 0)),
            str(rdo_job.get("FAILURE", 0)),
            str(rdo_job.get("OTHER", 0)),
            str(upstream_job.get("SUCCESS", 0)),
            str(upstream_job.get("FAILURE", 0)),
            str(upstream_job.get("OTHER", 0))
        )
    console.print(table)


def load_conf_file(config_file):
    config = {}
    with open(config_file, "r") as file:
        config = yaml.safe_load(file)
    return config


def query_zuul(job_names, limit, url):
    logging.debug("Querying zuul %s for jobs: %s", url, job_names)
    response = requests.get(
        url,
        params={'job_name': job_names, 'limit': limit},
        headers={'Accept': 'application/json'}
    )
    logging.debug("Return zuul response")
    return response.json()


def query_zuul_job_details(
        job_names, limit=ZUUL_JOBS_LIMIT,
        url="https://review.rdoproject.org/zuul/api/builds"):

    logging.debug("Parsing jobs details")
    zuul_jobs = query_zuul(job_names, limit, url)

    jobs = {}
    for job in zuul_jobs:
        log_url = job['log_url']
        if not log_url:
            continue

        jobs[log_url] = job
    logging.debug("Done parsing jobs details")
    return jobs


def query_zuul_job_history(
        job_names, limit=ZUUL_JOBS_LIMIT,
        url="https://review.rdoproject.org/zuul/api/builds"):
    logging.debug("Parsing jobs history")

    if not ("rdo" in url or "redhat" in url):
        logging.debug("Preparing upstream jobs")
        # NOTE(dasm): Upstream job

        job_names_upstream = set()
        for job_name in job_names:
            if 'featureset' in job_name:
                # NOTE(dasm): Featureset jobs do not exist upstream
                continue

            job_matched = ZUUL_JOB_REGEX.match(job_name)
            if job_matched:
                job_names_upstream.add(job_matched.group('job_name'))
        job_names = job_names_upstream

    zuul_jobs = query_zuul(job_names, limit, url)

    jobs = {}
    for job in zuul_jobs:
        job_name = job.get('job_name')
        result = job.get('result')

        existing_job = jobs.get(job_name)
        if not existing_job:
            logging.debug("Adding %s", job_name)
            jobs[job_name] = {'SUCCESS': 0, 'FAILURE': 0, 'OTHER': 0}

        if (jobs[job_name]['SUCCESS'] + jobs[job_name]['FAILURE']
                + jobs[job_name]['OTHER']) >= ZUUL_JOB_HISTORY_THRESHOLD:
            continue

        if result == "SUCCESS":
            jobs[job_name]['SUCCESS'] += 1
        elif result == "FAILURE":
            jobs[job_name]['FAILURE'] += 1
        else:
            jobs[job_name]['OTHER'] += 1

    logging.debug("Done parsing jobs history")
    return jobs


def prepare_jobs(all_jobs, jobs_in_criteria, dlrn_jobs, zuul_jobs):
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
    """

    logging.info("Preparing InfluxDB jobs")
    job_result_list = []

    for idx, job_name in enumerate(sorted(all_jobs)):
        logging.info("Fetching job: %d: %s", idx, job_name)
        job = dlrn_jobs.get(job_name)

        # NOTE(dasm):
        # DLRN returns job.url without trailing '/'
        log_url = job.url + '/' if job else "N/A"

        zuul_job = zuul_jobs.get(log_url)
        if not zuul_job:
            logging.error('Missing job %s', log_url)
            zuul_job = {}

        if job and job.success is True:
            status = INFLUX_PASSED
        elif job and job.success is False:
            status = INFLUX_FAILED
        else:
            status = INFLUX_PENDING

        job_result = {
            'job_name': job_name,
            'criteria': job_name in jobs_in_criteria,
            'logs': log_url,
            'duration': zuul_job.get('duration', 0),
            'status': status,
            'failure_reason': zuul_job.get('error_detail', 'N/A'),
        }
        job_result_list.append(job_result)
    return job_result_list


def prepare_render_template(filename):
    path = os.path.dirname(__file__)
    file_loader = FileSystemLoader(path + '/templates')
    env = Environment(loader=file_loader)
    template = env.get_template(filename)
    return template


def render_testproject_yaml(jobs, test_hash, testproject_url):
    template = prepare_render_template('.zuul.yaml.j2')
    output = template.render(
        jobs=jobs, hash=test_hash, testproject_url=testproject_url)
    print(output)


def render_influxdb(jobs, job_extra, promotion, promotion_extra):
    template = prepare_render_template('influx.j2')
    output = template.render(
        jobs=jobs, job_extra=job_extra, promotion=promotion,
        promotion_extra=promotion_extra)
    print(output)


def print_tables(
        timestamp, hut, no_result,
        compare_upstream, component, components,
        pkg_diff, test_hash, periodic_builds_url,
        upstream_builds_url, testproject_url, jobs=None):
    """
    jobs_to_promote are any job that hasn't registered
    success w/ dlrn. jobs_pending are any jobs in pending.
    We only want test project config for jobs that have completed.
    execute if there are failing jobs in criteria and if
    you are only looking at one component and not all components
    """
    jobs_passed = {}
    jobs_failed = {}
    to_promote = set()
    jobs_to_promote = {}
    for job in jobs:
        if job['criteria'] and job['status'] == INFLUX_PASSED:
            jobs_passed[job['job_name']] = job
        elif job['status'] == INFLUX_FAILED:
            jobs_failed[job['job_name']] = job
            if job['criteria']:
                to_promote.add(job['job_name'])
                jobs_to_promote[job['job_name']] = job
        elif job['criteria']:
            to_promote.add(job['job_name'])
        else:
            # NOTE(dasm): Job outside of promotion criteria
            continue

    if jobs_failed:
        status = "Red"
    elif not to_promote:
        status = "Green"
    else:
        status = "Yellow"

    component_ui = f"{component} component" if component else ""
    status_ui = f"status={status}"
    promotion_ui = f"last_promotion={timestamp}"
    hash_ui = f"Hash_under_test={hut}"
    header_ui = " ".join([component_ui, status_ui, promotion_ui])

    console.print(header_ui)
    console.print(hash_ui)

    print_a_set_in_table(jobs_passed.keys(), "Jobs which passed:")
    print_a_set_in_table(jobs_failed.keys(), "Jobs which failed:")
    print_a_set_in_table(no_result, "Pending running jobs")
    print_failed_in_criteria(to_promote,
                             periodic_builds_url,
                             upstream_builds_url)
    if jobs_failed:
        console.print("Logs of failing jobs:")
    for job_name, job_values in jobs_failed.items():
        console.print(job_values['logs'])

    if pkg_diff:
        console.print("\n Packages Tested")
        rich_print(pkg_diff)

    # NOTE: Print new line to separate results
    console.print("\n")

    tp_jobs = to_promote - no_result
    if tp_jobs and len(components) == 1:
        render_testproject_yaml(tp_jobs, test_hash, testproject_url)


def integration(
        api_url, base_url, aggregate_hash, promo_aggregate_hash):

    commit_url = f"{base_url}{aggregate_hash}/delorean.repo.md5"
    ref_hash = web_scrape(commit_url)
    api_response = find_results_from_dlrn_agg(api_url, ref_hash)

    under_test_url = (f"{api_url}/api/civotes_agg_detail.html?"
                      f"ref_hash={ref_hash}")
    promoted_url = (f"{api_url}/api/civotes_agg_detail.html?"
                    f"ref_hash={promo_aggregate_hash}")
    return api_response, ref_hash, under_test_url, promoted_url


def track_integration_promotion(
        config, distro, release, influx, stream, compare_upstream,
        promotion_name, aggregate_hash):

    url = config[stream]['criteria'][distro][release]['int_url']
    api_url, base_url = gather_basic_info_from_criteria(url)

    promotion = get_dlrn_promotions(api_url, promotion_name)

    api_response, test_hash, under_test_url, promoted_url = integration(
        api_url, base_url, aggregate_hash, promotion.aggregate_hash)

    component = None
    last_modified = get_last_modified_date(base_url, component)
    promotion_extra = {
        'release': release,
        'distro': distro,
        'dlrn_details': promoted_url,
        'last_modified': last_modified,
    }

    dlrn_jobs = get_dlrn_results(api_response)
    jobs_results = set(dlrn_jobs.keys())

    jobs_in_criteria = find_jobs_in_integration_criteria(
        url, promotion_name=promotion_name)
    jobs_pending = jobs_in_criteria.difference(jobs_results)

    all_jobs = jobs_results.union(jobs_in_criteria)

    job_extra = {
        'distro': distro,
        'release': release,
        'component': component,
        'job_type': "component" if component else "integration",
        'promote_name': promotion_name,
        'test_hash': test_hash
    }
    periodic_builds_url = config[stream]['periodic_builds_url']
    upstream_builds_url = config[stream]['upstream_builds_url']
    testproject_url = config[stream]['testproject_url']
    timestamp = datetime.utcfromtimestamp(promotion.timestamp)

    components, pkg_diff = get_components_diff(
        base_url, component, promotion_name, aggregate_hash)

    zuul_jobs = query_zuul_job_details(all_jobs)
    jobs = prepare_jobs(all_jobs, jobs_in_criteria, dlrn_jobs, zuul_jobs)
    if influx:
        render_influxdb(jobs, job_extra, promotion, promotion_extra)
    else:
        print_tables(
            timestamp, under_test_url,
            jobs_pending,
            compare_upstream, component, components,
            pkg_diff, test_hash, periodic_builds_url,
            upstream_builds_url, testproject_url, jobs)


def get_components_diff(
        base_url, component, promotion_name, aggregate_hash):
    logging.debug("Get components diff")
    components = sorted(ALL_COMPONENTS.difference(["all"]))
    pkg_diff = None

    if component != "all":
        logging.debug("Getting component diff for %s", component)
        # get package diff for the component # control_url
        control_url = get_dlrn_versions_csv(
            base_url, component, promotion_name)
        control_csv = get_csv(control_url)

        # test_url, what is currently getting tested
        test_url = get_dlrn_versions_csv(
            base_url, component, aggregate_hash)
        test_csv = get_csv(test_url)

        components = [component]
        pkg_diff = get_diff(
            promotion_name, control_csv, aggregate_hash, test_csv)

    return components, pkg_diff


def track_component_promotion(
        config, distro, release, influx, stream, compare_upstream,
        test_component):
    url = config[stream]['criteria'][distro][release]['comp_url']
    api_url, base_url = gather_basic_info_from_criteria(url)
    api_suffix = "api/civotes_detail.html?commit_hash="

    promotion_name = "current-tripleo"
    aggregate_hash = "component-ci-testing"
    components, pkg_diff = get_components_diff(
        base_url, test_component, promotion_name, aggregate_hash)

    periodic_builds_url = config[stream]['periodic_builds_url']
    upstream_builds_url = config[stream]['upstream_builds_url']
    testproject_url = config[stream]['testproject_url']

    for component in components:
        commit_hash, distro_hash, extended_hash = fetch_hashes_from_commit_yaml(
            f"{base_url}component/{component}/"
            "component-ci-testing/commit.yaml")
        api_response = find_results_from_dlrn_repo_status(
            api_url, commit_hash, distro_hash, extended_hash)

        promotion = get_dlrn_promotions(
            api_url, "promoted-components", component=component)
        timestamp = datetime.utcfromtimestamp(promotion.timestamp)

        promoted_hash = "{}/{}{}&distro_hash={}".format(
            api_url, api_suffix,
            promotion.commit_hash, promotion.distro_hash)

        last_modified = get_last_modified_date(base_url, component)
        promotion_extra = {
            'release': release,
            'distro': distro,
            'dlrn_details': promoted_hash,
            'last_modified': last_modified,
        }

        dlrn_jobs = get_dlrn_results(api_response)
        jobs_results = set(dlrn_jobs.keys())

        jobs_in_criteria = find_jobs_in_component_criteria(url, component)
        jobs_pending = jobs_in_criteria.difference(jobs_results)

        all_jobs = jobs_results.union(jobs_in_criteria)

        job_extra = {
            'distro': distro,
            'release': release,
            'component': component,
            'job_type': "component" if component else "integration",
            'promote_name': 'promoted-components',
            'test_hash': f"{commit_hash}_{distro_hash[:8]}",
        }
        test_hash = commit_hash
        hash_under_test = "{}/{}{}&distro_hash={}".format(
            api_url, api_suffix, commit_hash, distro_hash)

        zuul_jobs = query_zuul_job_details(all_jobs)
        jobs = prepare_jobs(all_jobs, jobs_in_criteria, dlrn_jobs, zuul_jobs)
        if influx:
            render_influxdb(jobs, job_extra, promotion, promotion_extra)
        else:
            print_tables(
                timestamp, hash_under_test,
                jobs_pending,
                compare_upstream, component, components,
                pkg_diff, test_hash, periodic_builds_url,
                upstream_builds_url, testproject_url, jobs)


@ click.command()
@click.option("--verbose", is_flag=True, default=False)
@ click.option("--release", default='master',
               type=click.Choice(RELEASES))
@ click.option("--distro", default='centos-9',
               type=click.Choice(DISTROS))
@ click.option("--component",
               type=click.Choice(sorted(ALL_COMPONENTS)))
@ click.option("--influx", is_flag=True, default=False)
@ click.option("--compare_upstream", is_flag=True, default=False)
@ click.option("--aggregate_hash",
               required=False,
               default="tripleo-ci-testing",
               # TO-DO w/ tripleo-get-hash
               help=("default:tripleo-ci-testing"
                     "\nexample:tripleo-ci-testing/e6/ad/e6ad..."))
@ click.option("--promotion_name", required=False, default="current-tripleo",
               type=click.Choice(["current-tripleo", "current-tripleo-rdo"]))
@ click.option("--config_file", default=os.path.dirname(__file__)
               + '/conf_ruck_rover.yaml')
def main(release,
         distro,
         config_file,
         influx=False,
         component=None,
         compare_upstream=False,
         aggregate_hash="tripleo-ci-testing",
         promotion_name="current-tripleo",
         verbose=False):

    if verbose:
        fmt = '%(asctime)s:%(levelname)s - %(funcName)s:%(lineno)s %(message)s'
        logging.basicConfig(format=fmt, encoding='utf-8', level=logging.DEBUG)

    stream = 'upstream'
    if release in ('osp16-2', 'osp17'):
        stream = 'downstream'
        if config_file != os.path.dirname(__file__) + '/conf_ruck_rover.yaml':
            print('using custom config file: {}'.format(config_file))
        else:
            downstream_urls = 'https://url.corp.redhat.com/ruck-rover-0'
            config_file = download_file(downstream_urls)
    config = load_conf_file(config_file)

    distros = REVERSED_MATRIX[release]
    releases = MATRIX[distro]
    if distro not in distros or release not in releases:
        msg = f'Release {release} is not supported for {distro}.'
        raise BadParameter(msg)

    if component:
        track_component_promotion(
            config, distro, release, influx, stream, compare_upstream,
            component)
    else:
        track_integration_promotion(
            config, distro, release, influx, stream, compare_upstream,
            promotion_name, aggregate_hash)


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter
