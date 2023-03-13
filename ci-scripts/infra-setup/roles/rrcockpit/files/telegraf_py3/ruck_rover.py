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

# Use user-provided CA bundle or fallback to system-provided CA bundle.
# Ensure that your CA bundle includes Red Hat's certificate authority,
# because downstream uses self-signed certificates in certificate chain.
# Requests uses certificates from the package certifi by default which
# is missing Red Hat's certificate authority.
CERT_PATH = os.environ.get(
                'CURL_CA_BUNDLE',
                '/etc/pki/ca-trust/extracted/openssl/ca-bundle.trust.crt')
dlrnapi_client.configuration.ssl_ca_cert = CERT_PATH

MATRIX = {
    "centos-8": ["wallaby", "train"],
    "centos-9": ["master", "zed", "wallaby"],
    "rhel-8": ["osp17-1", "osp16-2"],
    "rhel-9": ["osp17", "osp17-1", "osp18"]
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
ZUUL_JOB_REGEX = re.compile(r"periodic-(?P<job_name>.*)-\w*")


def download_file(url):
    logging.debug("Download a file: %s", url)
    response = requests.get(url, stream=True, verify=CERT_PATH)
    response.raise_for_status()
    file_descriptor, path = mkstemp(prefix="job-output-")
    with open(path, "wb") as file:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                file.write(chunk)
    os.close(file_descriptor)

    logging.debug("Downloaded a file: %s", path)
    return path


def find_failure_reason(url):
    if url == "N/A":
        return "N/A"

    url = f'{url}logs/failures_file'
    logging.debug("Fetch failure reason: %s", url)
    try:
        response = requests.get(url, verify=CERT_PATH)
    except requests.exceptions.RequestException:
        logging.info("Cannot connect to the url")
        return "N/A"

    if response.ok:
        logging.debug("Fetched failure reason")
        return ' '.join(response.text.split('\n'))

    logging.debug("Failed fetching reason")
    return "N/A"


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


def gather_basic_info_from_criteria(criteria):
    api_url = criteria['api_url']
    base_url = criteria['base_url']

    return api_url, base_url


def find_jobs_in_integration_criteria(
        criteria, promotion_name='current-tripleo'):
    return set(criteria['promotions'][promotion_name]['criteria'])


def find_jobs_in_integration_alt_criteria(
        criteria, promotion_name='current-tripleo'):
    return criteria['promotions'][promotion_name].get(
            'alternative_criteria', {})


def find_jobs_in_component_criteria(criteria, component):
    # In component criteria file, when a new pipeline
    # is developed, We donot add jobs to the criteria file and it will
    # return empty list. This case needs to be handled to avoid breakage.
    jobs = criteria['promoted-components'][component]
    if jobs is None:
        jobs = []
    return set(jobs)


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

    api_client = dlrnapi_client.ApiClient(host=api_url)
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


def upstream_job(job_name):
    """Get upstream job name from midstream job.

    :param job_name (str): midstream job name
    :return name_matched (str): upstream job name or empty string
    """
    name_matched = ""
    if 'featureset' in job_name:
        # NOTE(dasm): Featureset jobs do not exist upstream
        return name_matched

    job_matched = ZUUL_JOB_REGEX.match(job_name)
    if job_matched:
        name_matched = job_matched.group('job_name')
        logging.debug("Matched name: %s -> %s", job_name, name_matched)
    return name_matched


def get_upstream_jobs(jobs):
    job_names_upstream = set()
    for job_name in jobs:
        name_matched = upstream_job(job_name)
        job_names_upstream.add(name_matched)

    return job_names_upstream


def get_job_history(jobs, url):
    """Fetch jobs history from provided URL.

    :param jobs (set): Set of job names
    :param url (str): URL to fetch job history from.
    :return history (dict): Summary of history for all jobs.
    """
    if not jobs:
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
    for index, job in enumerate(response.json()):
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


def print_failed_in_criteria(jobs, upstream_history):
    """Print jobs history.

    : param jobs (dict): History of jobs running upstream and midstream.
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
    table.add_column("Upstream Pass", width=15)
    table.add_column("Upstream Failure", width=15)
    table.add_column("Upstream Others", width=15)

    no_upstream_job_stats = {
        "SUCCESS": "-",
        "FAILURE": "-",
        "OTHER": "-",
    }
    for job_name, job_stats in sorted(jobs.items()):
        upstream_job_name = upstream_job(job_name)
        upstream_job_stats = upstream_history.get(
            upstream_job_name, no_upstream_job_stats)

        table.add_row(
            job_name,
            str(job_stats['SUCCESS']),
            str(job_stats['FAILURE']),
            str(job_stats['OTHER']),
            str(upstream_job_stats['SUCCESS']),
            str(upstream_job_stats['FAILURE']),
            str(upstream_job_stats['OTHER'])
        )
    console.print(table)


def load_conf_file(config_file):
    config = {}
    with open(config_file, "r") as file:
        config = yaml.safe_load(file)
    return config


def query_zuul_job_details(
        job_names,
        url="https://review.rdoproject.org/zuul/api/builds"):

    logging.debug("Query ZUUL")
    logging.debug("Job names: %s", job_names)
    response = requests.get(
        url,
        params={'job_name': job_names, 'limit': ZUUL_JOBS_LIMIT},
        headers={'Accept': 'application/json'}
    )

    jobs = {}
    for job in response.json():
        log_url = job['log_url']
        if not log_url:
            continue

        jobs[log_url] = job
    logging.debug("Return ZUUL details")
    return jobs


def prepare_jobs(
        jobs_in_criteria,
        jobs_in_alt_criteria,
        dlrn_jobs,
        influx):
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

    logging.debug("Preparing influxdb")

    all_jobs = set(dlrn_jobs).union(jobs_in_criteria)

    zuul_jobs = {}
    if influx:
        logging.debug("Fetch jobs details")
        zuul_jobs = query_zuul_job_details(all_jobs)

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
            'failure_reason': (find_failure_reason(log_url)
                               if status == INFLUX_FAILED else "N/A"),
        }
        job_result_list.append(job_result)
    logging.debug("Prepared influxdb: %s", job_result_list)

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


def render_influxdb(jobs, job_extra, promotion, promotion_extra):
    template = prepare_render_template('influx.j2')
    output = template.render(
        jobs=jobs, job_extra=job_extra, promotion=promotion,
        promotion_extra=promotion_extra)
    print(output)


def render_tables(jobs, timestamp, under_test_url, component,
                  components, api_response, pkg_diff, test_hash,
                  periodic_builds_url, upstream_builds_url, testproject_url):
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

    upstream_jobs = get_upstream_jobs(to_promote)
    periodic_history = get_job_history(to_promote, periodic_builds_url)
    upstream_history = get_job_history(upstream_jobs, upstream_builds_url)

    print_failed_in_criteria(periodic_history, upstream_history)

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


def integration(
        api_url, base_url, aggregate_hash, promo_aggregate_hash):

    commit_url = f"{base_url}{aggregate_hash}/delorean.repo.md5"
    ref_hash = web_scrape(commit_url)
    api_response = find_results_from_dlrn_agg(api_url, ref_hash)

    under_test_url = (f"{api_url}/api/civotes_agg_detail.html?"
                      f"ref_hash={ref_hash}")
    return api_response, ref_hash, under_test_url


def track_integration_promotion(
        config, distro, release, stream, promotion_name,
        aggregate_hash):

    logging.debug("Starting integration track")
    url = config[stream]['criteria'][distro][release]['int_url']
    criteria = url_response_in_yaml(url)
    api_url, base_url = gather_basic_info_from_criteria(criteria)

    promotion = get_dlrn_promotions(api_url, promotion_name)

    api_response, test_hash, under_test_url = integration(
        api_url, base_url, aggregate_hash, promotion.aggregate_hash)

    component = None

    periodic_builds_url = config[stream]['periodic_builds_url']
    upstream_builds_url = config[stream]['upstream_builds_url']
    testproject_url = config[stream]['testproject_url']
    timestamp = datetime.utcfromtimestamp(promotion.timestamp)

    components, pkg_diff = get_components_diff(
        base_url, component, promotion_name, aggregate_hash)

    jobs_in_criteria = find_jobs_in_integration_criteria(
        criteria, promotion_name)
    jobs_in_alt_criteria = find_jobs_in_integration_alt_criteria(
        criteria, promotion_name)
    dlrn_jobs = get_dlrn_results(api_response)
    jobs = prepare_jobs(
            jobs_in_criteria,
            jobs_in_alt_criteria,
            dlrn_jobs,
            influx=False)

    render_tables(
        jobs, timestamp, under_test_url, component,
        components, api_response, pkg_diff, test_hash,
        periodic_builds_url, upstream_builds_url, testproject_url)

    logging.debug("Finished integration track")


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
        config, distro, release, stream, test_component):
    logging.debug("Starting component track")

    url = config[stream]['criteria'][distro][release]['comp_url']
    criteria = url_response_in_yaml(url)
    api_url, base_url = gather_basic_info_from_criteria(criteria)
    api_suffix = "api/civotes_detail.html?commit_hash="

    promotion_name = "current-tripleo"
    aggregate_hash = "component-ci-testing"
    components, pkg_diff = get_components_diff(
        base_url, test_component, promotion_name, aggregate_hash)

    periodic_builds_url = config[stream]['periodic_builds_url']
    upstream_builds_url = config[stream]['upstream_builds_url']
    testproject_url = config[stream]['testproject_url']

    for component in components:
        logging.debug("Fetching component: %s data", component)
        component_url = (f"{base_url}component/{component}/"
                         "component-ci-testing/commit.yaml")
        component_criteria = url_response_in_yaml(component_url)
        commit_hash, distro_hash, extended_hash = fetch_hashes_from_commit_yaml(
            component_criteria)
        api_response = find_results_from_dlrn_repo_status(
            api_url, commit_hash, distro_hash, extended_hash)

        promotion = get_dlrn_promotions(
            api_url, "promoted-components", component)
        timestamp = datetime.utcfromtimestamp(promotion.timestamp)

        test_hash = commit_hash
        under_test_url = "{}/{}{}&distro_hash={}".format(
            api_url, api_suffix, commit_hash, distro_hash)

        jobs_in_criteria = find_jobs_in_component_criteria(criteria, component)
        dlrn_jobs = get_dlrn_results(api_response)
        jobs = prepare_jobs(jobs_in_criteria, {}, dlrn_jobs,
                            influx=False)

        render_tables(
            jobs, timestamp, under_test_url, component,
            components, api_response, pkg_diff, test_hash,
            periodic_builds_url, upstream_builds_url, testproject_url)
        logging.debug("Finished component: %s data", component)

    logging.debug("Finshed component track")


def integration_influx(config, distro, release, stream, promotion_name):
    url = config[stream]['criteria'][distro][release]['int_url']
    criteria = url_response_in_yaml(url)
    api_url, base_url = gather_basic_info_from_criteria(criteria)

    promotion = get_dlrn_promotions(api_url, promotion_name)

    aggregate_hash = "tripleo-ci-testing"
    commit_url = f"{base_url}{aggregate_hash}/delorean.repo.md5"
    test_hash = web_scrape(commit_url)
    promoted_url = (f"{api_url}/api/civotes_agg_detail.html?"
                    f"ref_hash={promotion.aggregate_hash}")

    api_response = find_results_from_dlrn_agg(api_url, test_hash)

    component = None
    last_modified = get_last_modified_date(base_url, component)
    promotion_extra = {
        'release': release,
        'distro': distro,
        'dlrn_details': promoted_url,
        'last_modified': last_modified,
    }

    job_extra = {
        'distro': distro,
        'release': release,
        'component': component,
        'job_type': "component" if component else "integration",
        'promote_name': promotion_name,
        'test_hash': test_hash
    }

    jobs_in_criteria = find_jobs_in_integration_criteria(
        criteria, promotion_name)
    dlrn_jobs = get_dlrn_results(api_response)
    jobs_in_alt_criteria = find_jobs_in_integration_alt_criteria(
        criteria, promotion_name)
    jobs = prepare_jobs(jobs_in_criteria, jobs_in_alt_criteria,
                        dlrn_jobs, influx=True)
    render_influxdb(jobs, job_extra, promotion, promotion_extra)


def component_influx(config, distro, release, stream, test_component):
    url = config[stream]['criteria'][distro][release]['comp_url']
    criteria = url_response_in_yaml(url)
    api_url, base_url = gather_basic_info_from_criteria(criteria)

    if test_component and test_component != "all":
        components = [test_component]
    else:
        components = sorted(ALL_COMPONENTS.difference(["all"]))

    all_dlrn_jobs = {}
    all_jobs_in_criteria = set()

    job_response = {}
    component_response = {}
    for component in components:
        promotion = get_dlrn_promotions(
            api_url, "promoted-components", component)
        component_url = (
            f"{base_url}component/{component}/component-ci-testing/commit.yaml"
        )

        promoted_url = (
            f"{api_url}/api/civotes_detail.html?"
            f"commit_hash={promotion.commit_hash}&"
            f"distro_hash={promotion.distro_hash}"
        )
        component_criteria = url_response_in_yaml(component_url)
        commit_hash, distro_hash, extended_hash = fetch_hashes_from_commit_yaml(
            component_criteria)
        api_response = find_results_from_dlrn_repo_status(
            api_url, commit_hash, distro_hash, extended_hash)

        dlrn_jobs = get_dlrn_results(api_response)
        jobs_in_criteria = find_jobs_in_component_criteria(criteria, component)

        component_response[component] = {
            'job_extra': {
                'distro': distro,
                'release': release,
                'component': component,
                'job_type': "component" if component else "integration",
                'promote_name': 'promoted-components',
                'test_hash': f"{commit_hash}_{distro_hash[:8]}",
            },
            'promotion_extra': {
                'distro': distro,
                'release': release,
                'dlrn_details': promoted_url,
                'last_modified': get_last_modified_date(base_url, component),
            },
            'promotion': promotion,
        }

        all_jobs = set(dlrn_jobs).union(jobs_in_criteria)
        for job_name in all_jobs:
            job_response[job_name] = {
                'component': component,
            }

        all_dlrn_jobs.update(dlrn_jobs)
        all_jobs_in_criteria.update(jobs_in_criteria)

    components = {}

    jobs = prepare_jobs(all_jobs_in_criteria, {},
                        all_dlrn_jobs, influx=True)
    # NOTE(dasm): Map job name to component
    for job in jobs:
        job_name = job['job_name']
        component = job_response[job_name]['component']
        components.setdefault(component, []).append(job)

    for component, jobs in sorted(components.items()):
        job_extra = component_response[component]['job_extra']
        promotion = component_response[component]['promotion']
        promotion_extra = component_response[component]['promotion_extra']

        render_influxdb(jobs, job_extra, promotion, promotion_extra)


@click.option("--verbose", is_flag=True, default=False)
@click.option("--influx", is_flag=True, default=False)
@click.option("--component", default=None,
              type=click.Choice(sorted(ALL_COMPONENTS)))
@click.option("--aggregate_hash", default="tripleo-ci-testing",
              # TO-DO w/ tripleo-get-hash
              help=("default:tripleo-ci-testing"
                    "\nexample:tripleo-ci-testing/e6/ad/e6ad..."))
@click.option("--promotion_name", default="current-tripleo",
              type=click.Choice(["current-tripleo", "current-tripleo-rdo"]))
@click.option("--config_file", default=os.path.dirname(__file__)
              + '/conf_ruck_rover.yaml')
@click.option("--distro", default='centos-9', type=click.Choice(DISTROS))
@click.option("--release", default='master', type=click.Choice(RELEASES))
@click.command()
def main(release, distro, config_file, promotion_name, aggregate_hash,
         component, influx, verbose):

    if verbose:
        fmt = '%(asctime)s:%(levelname)s - %(funcName)s:%(lineno)s %(message)s'
        logging.basicConfig(format=fmt, encoding='utf-8', level=logging.DEBUG)

    stream = 'upstream'
    if release in ('osp16-2', 'osp17', 'osp17-1', 'osp18'):
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

    logging.info("Starting script: %s - %s", distro, release)
    if influx and component:
        component_influx(config, distro, release, stream, component)
    elif influx and not component:
        integration_influx(config, distro, release, stream, promotion_name)
    elif not influx and component:
        track_component_promotion(config, distro, release, stream, component)
    elif not influx and not component:
        track_integration_promotion(
            config, distro, release, stream, promotion_name, aggregate_hash)
    else:
        raise Exception("Unsupported")
    logging.info("Finished script: %s - %s", distro, release)


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter
