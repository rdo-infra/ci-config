#!/usr/bin/env python

import csv
import json
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
    "centos-7": ["train"],
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


def date_diff_in_seconds(dt2, dt1):
    timedelta = dt2 - dt1

    return timedelta.days * 24 * 3600 + timedelta.seconds


def dhms_from_seconds(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    return (hours, minutes, seconds)


def strip_date_time_from_string(input_string):
    regex_object = re.compile(r'[\d*-]*\d* [\d*:]*')

    return regex_object.search(input_string).group()


def convert_string_date_object(date_string):
    return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')


def download_file(url):
    response = requests.get(url, stream=True, verify=CERT_PATH)
    response.raise_for_status()
    file_descriptor, path = mkstemp(prefix="job-output-")
    with open(path, "wb") as file:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                file.write(chunk)
    os.close(file_descriptor)

    return path


def delete_file(path):
    os.remove(path)


def find_job_run_time(url):
    try:
        path = download_file(url + "/job-output.txt")
    except requests.exceptions.RequestException:
        return "N/A"
    with open(path, "r") as file:
        first_line = file.readline()
        for last_line in file:
            pass
    start_time = strip_date_time_from_string(first_line)
    start_time_ob = convert_string_date_object(start_time)
    end_time = strip_date_time_from_string(last_line)
    end_time_ob = convert_string_date_object(end_time)

    hours, minutes, seconds = dhms_from_seconds(
        date_diff_in_seconds(end_time_ob, start_time_ob))
    delete_file(path)

    return f"{hours} hr {minutes} mins {seconds} secs"


def find_failure_reason(url):
    try:
        path = download_file(url + "/logs/failures_file")
    except requests.exceptions.RequestException:
        return "N/A"
    with open(path, "r") as file:
        first_line = file.readline()
    delete_file(path)

    return first_line.rstrip()


def web_scrape(url):
    try:
        response = requests.get(url, verify=CERT_PATH)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err)
    except requests.exceptions.RequestException as error:
        raise SystemExit(error)

    return response.text


def url_response_in_yaml(url):
    text_response = web_scrape(url)
    processed_data = yaml.safe_load(text_response)

    return processed_data


def gather_basic_info_from_criteria(url):
    criteria_content = url_response_in_yaml(url)
    api_url = criteria_content['api_url']
    base_url = criteria_content['base_url']

    return api_url, base_url


def find_jobs_in_integration_criteria(url, promotion_name='current-tripleo'):
    criteria_content = url_response_in_yaml(url)

    return criteria_content['promotions'][promotion_name]['criteria']


def find_jobs_in_component_criteria(url, component):
    criteria_content = url_response_in_yaml(url)

    return set(criteria_content['promoted-components'][component])


def fetch_hashes_from_commit_yaml(url):
    """
    This function finds commit hash, distro hash, extended_hash from commit.yaml
    :param url for commit.yaml
    :returns strings for commit_hash, distro_hash, extended_hash
    """
    commit_yaml_content = url_response_in_yaml(url)
    commit_hash = commit_yaml_content['commits'][0]['commit_hash']
    distro_hash = commit_yaml_content['commits'][0]['distro_hash']
    extended_hash = commit_yaml_content['commits'][0]['extended_hash']

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


def get_consistent(url, component=None):
    """Get the date of the consistent link in dlrn.
    """

    if "centos7" in url:
        dlrn_tag = "consistent"
        short_url = url.split("/")[:-3]
    else:
        dlrn_tag = "promoted-components"
        short_url = url.split("/")[:-5]

    repo = "delorean.repo"
    short_url = "/".join(short_url)

    if component is None:
        # integration build, use last promoted_components date
        url = f'{short_url}/{dlrn_tag}/{repo}'
    else:
        # TO-DO normalize component and intergration config
        url = f'{short_url}/component/{component}/consistent/{repo}'

    response = requests.get(url, verify=CERT_PATH)
    if not response.ok:
        return None

    cd = response.headers['Last-Modified']
    consistent_date = format_ts_from_last_modified(cd)
    return consistent_date


def get_dlrn_versions_csv(base_url, component, tag):
    component_part = f"/component/{component}" if component else ""
    return f"{base_url}{component_part}/{tag}/versions.csv"


def get_csv(url):
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
    api_client = dlrnapi_client.ApiClient(host=api_url)
    api_instance = dlrnapi_client.DefaultApi(api_client)
    query = dlrnapi_client.PromotionQuery(limit=1,
                                          promote_name=promotion_name)
    if component:
        query.component = component
    pr = api_instance.api_promotions_get_with_http_info(query)[0][0]
    consistent = get_consistent(pr.repo_url, component)
    promotion = {}
    promotion = pr.to_dict()
    promotion['latest_build'] = consistent
    return promotion


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
    if extended_hash == "None":
        extended_hash = None
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


def conclude_results_from_dlrn(api_response):
    passed_jobs = set()
    all_jobs_result_available = set()
    for job in api_response:
        all_jobs_result_available.add(job.job_id)
        if job.success:
            passed_jobs.add(job.job_id)

    failed_jobs = all_jobs_result_available.difference(passed_jobs)

    return all_jobs_result_available, passed_jobs, failed_jobs


def get_job_history(job_name, zuul, component=None):
    if 'rdo' in zuul or 'redhat' in zuul:
        url = zuul + "?job_name={}".format(job_name)

    else:
        # upstream
        upstream_job = job_name.split("-")
        # remove periodic-
        del upstream_job[0]
        # remove -branch
        del upstream_job[-1]
        if component:
            # component jobs remove both -master and -component
            del upstream_job[-1]

        upstream_job = '-'.join([str(elem) for elem in upstream_job])
        url = zuul + "?job_name={}".format(upstream_job)

    out = json.loads(web_scrape(url))

    # key job_name, value = { SUCCESS: count,
    #                         FAILURE: count,
    #                         OTHER: count}
    job_history = {}
    job_history[job_name] = {'SUCCESS': 0, 'FAILURE': 0, 'OTHER': 0}
    limit = 5
    for index, execution in enumerate(out):
        if index == limit:
            break
        if execution['result'] == "SUCCESS":
            job_history[job_name]['SUCCESS'] += 1
        elif execution['result'] == "FAILURE":
            job_history[job_name]['FAILURE'] += 1
        else:
            job_history[job_name]['OTHER'] += 1

    return job_history


def latest_job_results_url(api_response, all_jobs):
    logs_job = {}
    for particular_job in all_jobs:
        latest_log = {}
        for job in api_response:
            if job.job_id == particular_job:
                latest_log[job.timestamp] = job.url
        logs_job[particular_job] = latest_log[max(latest_log.keys())]

    return logs_job


def print_a_set_in_table(input_set, header="Job name"):
    table = Table(show_header=True, header_style="bold")
    table.add_column(header, style="dim", width=80)
    for job in input_set:
        table.add_row(job)
    console.print(table)


def print_failed_in_criteria(input_set,
                             config,
                             stream,
                             compare_upstream,
                             header="Job name",
                             component=None):

    table = Table(show_header=True, header_style="bold")
    table.add_column(header, width=80)
    table.add_column("Integration PASSED History", width=15)
    table.add_column("Integration FAILURE History", width=15)
    table.add_column("Integration Other History", width=15)
    if compare_upstream:
        table.add_column("Upstream PASSED History", width=10)
        table.add_column("Upstream FAILURE History", width=10)
        table.add_column("Upstream Other History", width=10)
    for job in input_set:
        int_history = get_job_history(job,
                                      config[stream]['periodic_builds_url'],
                                      component)
        if compare_upstream:
            upstream_builds_url = config[stream]['upstream_builds_url']
            # do not look for ovb jobs in upstream
            if "featureset" not in job:
                up_history = get_job_history(job,
                                             upstream_builds_url,
                                             component)
                table.add_row(job,
                              str(int_history[job]['SUCCESS']),
                              str(int_history[job]['FAILURE']),
                              str(int_history[job]['OTHER']),
                              str(up_history[job]['SUCCESS']),
                              str(up_history[job]['FAILURE']),
                              str(up_history[job]['OTHER']))
        else:
            table.add_row(job,
                          str(int_history[job]['SUCCESS']),
                          str(int_history[job]['FAILURE']),
                          str(int_history[job]['OTHER']))
    console.print(table)


def load_conf_file(config_file):
    config = {}
    with open(config_file, "r") as file:
        config = yaml.safe_load(file)
    return config


def print_influxdb(
        job_info, log_urls, all_jobs, passed_jobs, failed_jobs,
        jobs_in_criteria, promotions):
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

    job_result_list = []
    for job_name in sorted(all_jobs):
        if job_name in passed_jobs:
            status = INFLUX_PASSED
        elif job_name in failed_jobs:
            status = INFLUX_FAILED
        else:
            status = INFLUX_PENDING

        log_url = log_urls.get(job_name, "N/A")
        job_result = {
            'job_name': job_name,
            'criteria': job_name in jobs_in_criteria,
            'logs': log_url,
            'duration': find_job_run_time(log_url),
            'status': status,
            'failure_reason': (find_failure_reason(log_url)
                               if status == INFLUX_FAILED else "N/A"),
        }
        job_result.update(job_info)
        job_result_list.append(job_result)

    render_influxdb(job_result_list, promotions)


def prepare_render_template(filename):
    path = os.path.dirname(__file__)
    file_loader = FileSystemLoader(path + '/templates')
    env = Environment(loader=file_loader)
    template = env.get_template(filename)
    return template


def render_testproject_yaml(jobs, test_hash, stream, config):
    template = prepare_render_template('.zuul.yaml.j2')
    testproject_url = config[stream]['testproject_url']
    output = template.render(
        jobs=jobs, hash=test_hash, testproject_url=testproject_url)
    print(output)


def render_influxdb(jobs, promotion):
    template = prepare_render_template('influx.j2')
    output = template.render(jobs=jobs, promotion=promotion)
    print(output)


def track_integration_promotion(
        config, distro, release, influx, stream, compare_upstream,
        promotion_name, aggregate_hash):

    url = config[stream]['criteria'][distro][release]['int_url']
    dlrn_api_url, dlrn_trunk_url = gather_basic_info_from_criteria(url)
    promotions = get_dlrn_promotions(dlrn_api_url, promotion_name)
    promotions['release'] = release
    promotions['distro'] = distro

    if distro == "centos-7":
        commit_url = dlrn_trunk_url + aggregate_hash + '/commit.yaml'
        commit_hash, distro_hash, extended_hash = fetch_hashes_from_commit_yaml(
                                                    commit_url)

        test_hash = commit_hash
        api_response = find_results_from_dlrn_repo_status(
            dlrn_api_url, commit_hash, distro_hash, extended_hash)

        dlrn_api_suffix = "api/civotes_detail.html?commit_hash="
        hash_under_test = "{}/{}{}&distro_hash={}".format(
            dlrn_api_url, dlrn_api_suffix, commit_hash, distro_hash)
        promoted_hash = "{}/{}{}&distro_hash={}".format(
            dlrn_api_url, dlrn_api_suffix, promotions['commit_hash'],
            promotions['distro_hash'])
    else:
        md5sum_url = dlrn_trunk_url + aggregate_hash + '/delorean.repo.md5'
        test_hash = web_scrape(md5sum_url)
        api_response = find_results_from_dlrn_agg(dlrn_api_url, test_hash)

        dlrn_api_suffix = "api/civotes_agg_detail.html?ref_hash="
        hash_under_test = f"{dlrn_api_url}/{dlrn_api_suffix}{test_hash}"
        promoted_hash = (
            f"{dlrn_api_url}/{dlrn_api_suffix}{promotions['aggregate_hash']}")

    promotions['dlrn_details'] = promoted_hash

    (all_jobs_result_available,
     passed_jobs, failed_jobs) = conclude_results_from_dlrn(api_response)
    jobs_in_criteria = set(find_jobs_in_integration_criteria(
        url, promotion_name=promotion_name))
    jobs_which_need_pass_to_promote = jobs_in_criteria.difference(passed_jobs)
    jobs_with_no_result = jobs_in_criteria.difference(all_jobs_result_available)
    all_jobs = all_jobs_result_available.union(jobs_with_no_result)

    component = None
    job_info = {
        'distro': distro,
        'release': release,
        'component': component,
        'job_type': "component" if component else "integration",
        'promote_name': promotion_name,
        'test_hash': test_hash
    }
    if influx:
        # NOTE(dviroel): excluding jobs results from influx when promotion_name
        #  is "current-tripleo-rdo" since we are not using this info anywhere.
        if promotion_name != 'current-tripleo-rdo':
            # print out jobs in influxdb format
            log_urls = latest_job_results_url(
                api_response, all_jobs_result_available)
            print_influxdb(
                job_info, log_urls, all_jobs, passed_jobs,
                failed_jobs, jobs_in_criteria, promotions)
    else:
        last_p = datetime.utcfromtimestamp(promotions['timestamp'])
        console.print(f"Hash under test: {hash_under_test}",
                      f"\nlast_promotion={last_p}")
        print_a_set_in_table(passed_jobs, "Jobs which passed:")
        print_a_set_in_table(failed_jobs, "Jobs which failed:")
        print_a_set_in_table(jobs_with_no_result,
                             "Pending running jobs")
        needed_txt = ("Jobs which are in promotion criteria and need "
                      "pass to promote the Hash:")

        print_failed_in_criteria(jobs_which_need_pass_to_promote,
                                 config,
                                 stream,
                                 compare_upstream,
                                 needed_txt)
        console.print("Logs of jobs which are failing:-")
        log_urls = latest_job_results_url(
            api_response, failed_jobs)
        for value in log_urls.values():
            console.print(value)

        _, pkg_diff = get_components_diff(
            dlrn_trunk_url, None, promotion_name, aggregate_hash)
        if pkg_diff:
            console.print("\n Packages Tested")
            rich_print(pkg_diff)

        # jobs_which_need_pass_to_promote are any job that hasn't registered
        # success w/ dlrn.  jobs_with_no_result are any jobs in pending.
        # We only want test project config for jobs that have completed.
        tp_jobs = jobs_which_need_pass_to_promote - jobs_with_no_result
        if tp_jobs:
            render_testproject_yaml(tp_jobs, test_hash, stream, config)


def get_components_diff(
        dlrn_trunk_url, component, promotion_name, aggregate_hash):
    components = sorted(ALL_COMPONENTS.difference(["all"]))
    pkg_diff = None

    if component != "all":
        # get package diff for the component # control_url
        control_url = get_dlrn_versions_csv(
            dlrn_trunk_url, component, promotion_name)
        control_csv = get_csv(control_url)

        # test_url, what is currently getting tested
        test_url = get_dlrn_versions_csv(
            dlrn_trunk_url, component, aggregate_hash)
        test_csv = get_csv(test_url)

        components = [component]
        pkg_diff = get_diff(
            promotion_name, control_csv, aggregate_hash, test_csv)

    return components, pkg_diff


def track_component_promotion(
        config, distro, release, influx, stream, compare_upstream,
        test_component):
    url = config[stream]['criteria'][distro][release]['comp_url']
    dlrn_api_url, dlrn_trunk_url = gather_basic_info_from_criteria(url)
    dlrn_api_suffix = "api/civotes_detail.html?commit_hash="

    promotion_name = "current-tripleo"
    aggregate_hash = "component-ci-testing"
    components, pkg_diff = get_components_diff(
        dlrn_trunk_url, test_component, promotion_name, aggregate_hash)

    for component in components:
        commit_hash, distro_hash, extended_hash = fetch_hashes_from_commit_yaml(
            f"{dlrn_trunk_url}component/{component}/"
            "component-ci-testing/commit.yaml")
        api_response = find_results_from_dlrn_repo_status(
            dlrn_api_url, commit_hash, distro_hash, extended_hash)

        promotions = get_dlrn_promotions(
            dlrn_api_url, "promoted-components", component=component)
        promotions['release'] = release
        promotions['distro'] = distro

        promoted_hash = "{}/{}{}&distro_hash={}".format(
            dlrn_api_url, dlrn_api_suffix,
            promotions['commit_hash'], promotions['distro_hash'])
        promotions['dlrn_details'] = promoted_hash

        (all_jobs_result_available,
         passed_jobs, failed_jobs) = conclude_results_from_dlrn(api_response)
        if 'consistent' in all_jobs_result_available:
            all_jobs_result_available.remove('consistent')
        if 'consistent' in passed_jobs:
            passed_jobs.remove('consistent')
        if 'consistent' in failed_jobs:
            failed_jobs.remove('consistent')
        jobs_in_criteria = find_jobs_in_component_criteria(url, component)
        jobs_which_need_pass_to_promote = jobs_in_criteria.difference(
                                            passed_jobs)
        jobs_with_no_result = jobs_in_criteria.difference(
            all_jobs_result_available)
        all_jobs = all_jobs_result_available.union(jobs_with_no_result)

        job_info = {
            'distro': distro,
            'release': release,
            'component': component,
            'job_type': "component" if component else "integration",
            'promote_name': 'promoted-components',
            'test_hash': f"{commit_hash}_{distro_hash[:8]}",
        }
        if influx:
            log_urls = latest_job_results_url(
                api_response, all_jobs_result_available)
            print_influxdb(
                job_info, log_urls, all_jobs, passed_jobs,
                failed_jobs, jobs_in_criteria, promotions)

        else:
            log_urls = latest_job_results_url(
                api_response, failed_jobs)
            header = ("{} component jobs which need pass to promote "
                      "the hash: ").format(component)
            if failed_jobs:
                component_status = "Red"
            elif not jobs_which_need_pass_to_promote:
                component_status = "Green"
            else:
                component_status = "Yellow"
            last_p = datetime.utcfromtimestamp(promotions['timestamp'])

            hash_under_test = "{}/{}{}&distro_hash={}".format(
                dlrn_api_url, dlrn_api_suffix, commit_hash, distro_hash)
            console.print(f"{component} component",
                          f"status={component_status}",
                          f"last_promotion={last_p}",
                          f"\nHash_under_test={hash_under_test}")

            print_a_set_in_table(passed_jobs, "Jobs which passed:")
            if component_status != "Green":
                print_a_set_in_table(failed_jobs, "Jobs which failed:")
                print_a_set_in_table(jobs_with_no_result,
                                     "Pending running jobs")
                print_failed_in_criteria(jobs_which_need_pass_to_promote,
                                         config,
                                         stream,
                                         compare_upstream,
                                         header,
                                         component)
                if component_status == "Red":
                    console.print("Logs of failing jobs:")
                    for value in log_urls.values():
                        console.print(value)

            if pkg_diff:
                console.print("\nPackages Tested: {}".format(components[0]))
                rich_print(pkg_diff)
            print('\n')

            # jobs_which_need_pass_to_promote are any job that hasn't registered
            # success w/ dlrn.  jobs_with_no_result are any jobs in pending.
            # We only want test project config for jobs that have completed.
            tp_jobs = jobs_which_need_pass_to_promote - jobs_with_no_result
            # execute if there are failing jobs in criteria and if
            # you are only looking at one component and not all components
            if tp_jobs and len(components) == 1:
                render_testproject_yaml(tp_jobs, commit_hash, stream, config)


@ click.command()
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
         promotion_name="current-tripleo"):

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
        if distro == "centos-7":
            raise Exception("centos-7 components do not exist")

        track_component_promotion(
            config, distro, release, influx, stream, compare_upstream,
            component)
    else:
        track_integration_promotion(
            config, distro, release, influx, stream, compare_upstream,
            promotion_name, aggregate_hash)


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter
