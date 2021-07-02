#!/usr/bin/env python


import json
import os
import re
from datetime import datetime
from tempfile import mkstemp

import click
import dlrnapi_client
import requests
import yaml
from dlrnapi_client.rest import ApiException
from rich.console import Console
from rich.table import Table
from urllib3.exceptions import InsecureRequestWarning

console = Console()

# ZUUL_BUILDS_API
ZB_UPSTREAM = "https://zuul.openstack.org/api/builds"


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
    requests.packages.urllib3.disable_warnings(
        category=InsecureRequestWarning)
    response = requests.get(url, stream=True, verify=False)
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
        requests.packages.urllib3.disable_warnings(
            category=InsecureRequestWarning)
        response = requests.get(url, verify=False)
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


def find_jobs_in_integration_criteria(url):
    criteria_content = url_response_in_yaml(url)

    return criteria_content['promotions']['current-tripleo']['criteria']


def find_jobs_in_component_criteria(url, component):
    criteria_content = url_response_in_yaml(url)

    return criteria_content['promoted-components'][component]


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
        if job.job_id.startswith("periodic"):
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
                             zb_periodic,
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
        int_history = get_job_history(job, zb_periodic, component)

        if compare_upstream:
            up_history = get_job_history(job, ZB_UPSTREAM, component)
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


def load_conf_file(config_file, key):
    with open(config_file, "r") as file:
        config = yaml.safe_load(file)
        zuul_url = config['urls'][key]["zuul_url"]
        dlrnapi_url = config['urls'][key]["dlrnapi_url"]
        promoter_url = config['urls'][key]["promoter_url"]
        git_url = config['urls'][key]["git_url"]

    return zuul_url, dlrnapi_url, promoter_url, git_url


def influxdb(jobs_result):
    # https://docs.influxdata.com/influxdb/v2.0/reference/syntax/line-protocol/
    # jobs_result = the measurement
    # job_type is a tag, note the space
    # rest of the values are fields in a row of data

    # grafana can only color code w/ numbers, not text
    # 0 = failed, 5 = pending, 9 = success # grafana thresholds.
    if jobs_result['status'] == "failed":
        jobs_result['status'] = 0
    elif jobs_result['status'] == "pending":
        jobs_result['status'] = 5
    elif jobs_result['status'] == "passed":
        jobs_result['status'] = 9

    results_influxdb_line = ('jobs_result,'
                             'job_type={job_type},'
                             'job_name={job},'
                             'release={release} '
                             'name="{promote_name}",'
                             'test_hash="{test_hash}",'
                             'criteria="{criteria}",'
                             'status="{status}",'
                             'logs="{logs}",'
                             'failure_reason="{failure_reason}",'
                             'duration="{duration}",'
                             'component="{component}"')

    if jobs_result['component'] is None:
        jobs_result['job_type'] = "integration"
    else:
        jobs_result['job_type'] = "component"
    return results_influxdb_line.format(**jobs_result)


def track_integration_promotion(release,
                                distro,
                                dlrn_server,
                                promoter_base_url,
                                zb_periodic,
                                aggregate_hash='tripleo-ci-testing',
                                promotion="current-tripleo",
                                compare_upstream=False,
                                influx=False):
    if distro == "centos-8":
        promoter_path = "/config/CentOS-8/"
        dlrn_api_path = "api-centos8-"
        release_criteria = release
    elif distro == "centos-7":
        promoter_path = "/config/CentOS-7/"
        dlrn_api_path = "api-centos-"
        release_criteria = release
    elif distro == "rhel-8":
        promoter_path = "/config/RedHat-8/"
        dlrn_api_path = "api-rhel8-"
        if release == "osp16-2":
            release_criteria = "rhos-16.2"
        elif release == "osp17":
            release_criteria = "rhos-17"
    elif distro == "rhel-9":
        promoter_path = "/config/RedHat-9/"
        dlrn_api_path = "api-rhel9-"
        release_criteria = "rhos-17"

    promoter_url = promoter_base_url + promoter_path
    url = promoter_url + release_criteria + '.yaml'
    api_url, base_url = gather_basic_info_from_criteria(url)
    if distro != "centos-7":
        md5sum_url = base_url + aggregate_hash + '/delorean.repo.md5'
        test_hash = web_scrape(md5sum_url)
        api_response = find_results_from_dlrn_agg(api_url, test_hash)
    else:
        commit_url = base_url + aggregate_hash + '/commit.yaml'
        commit_hash, distro_hash, extended_hash = fetch_hashes_from_commit_yaml(
                                                    commit_url)
        api_response = find_results_from_dlrn_repo_status(api_url,
                                                          commit_hash,
                                                          distro_hash,
                                                          extended_hash)

    (all_jobs_result_available,
     passed_jobs, failed_jobs) = conclude_results_from_dlrn(api_response)
    jobs_in_criteria = set(find_jobs_in_integration_criteria(url))
    jobs_which_need_pass_to_promote = jobs_in_criteria.difference(passed_jobs)
    jobs_with_no_result = jobs_in_criteria.difference(all_jobs_result_available)
    all_jobs = all_jobs_result_available.union(jobs_with_no_result)
    if influx:
        log_urls = latest_job_results_url(
            api_response, all_jobs_result_available)
        for job in all_jobs:
            log_url = log_urls.get(job, "N/A")
            if job in passed_jobs:
                status = 'passed'
            elif job in failed_jobs:
                status = 'failed'
            else:
                status = 'pending'
            if status == 'failed':
                failure_reason = find_failure_reason(log_url)
            else:
                failure_reason = "N/A"
            jobs_result = {}
            jobs_result['release'] = release
            jobs_result['promote_name'] = promotion
            jobs_result['job'] = job
            jobs_result['test_hash'] = test_hash
            jobs_result['component'] = None
            jobs_result['criteria'] = job in jobs_in_criteria
            jobs_result['status'] = status
            jobs_result['logs'] = log_url
            jobs_result['failure_reason'] = failure_reason
            jobs_result['duration'] = find_job_run_time(
                log_url)
            print(influxdb(jobs_result))

    else:
        dlrn_api = dlrn_api_path + release
        if distro != "centos-7":
            dlrn_api_suffix = "api/civotes_agg_detail.html?ref_hash="
            # hash under test
            hut = "{}/{}/{}{}".format(dlrn_server,
                                      dlrn_api,
                                      dlrn_api_suffix,
                                      test_hash)
        else:
            dlrn_api_suffix = "api/civotes_detail.html?commit_hash="
            # hash under test
            hut = "{}/{}/{}{}&distro_hash={}".format(dlrn_server,
                                                     dlrn_api,
                                                     dlrn_api_suffix,
                                                     commit_hash,
                                                     distro_hash)

        console.print(f"Hash under test: {hut}")
        print_a_set_in_table(passed_jobs, "Jobs which passed:")
        print_a_set_in_table(failed_jobs, "Jobs which failed:")
        print_a_set_in_table(jobs_with_no_result,
                             "Pending running jobs")
        needed_txt = ("Jobs which are in promotion criteria and need "
                      "pass to promote the Hash:")
        print_failed_in_criteria(jobs_which_need_pass_to_promote,
                                 zb_periodic,
                                 compare_upstream,
                                 needed_txt)
        console.print("Logs of jobs which are failing:-")
        log_urls = latest_job_results_url(
            api_response, failed_jobs)
        for value in log_urls.values():
            console.print(value)


def track_component_promotion(release,
                              distro,
                              test_component,
                              git_base_url,
                              zb_periodic,
                              promotion="promoted-components",
                              compare_upstream=False,
                              influx=False):
    """ Find the failing jobs which are blocking promotion of a component.
    :param release: The OpenStack release e.g. wallaby
    :param component:
    """

    if distro == "centos-7":
        raise Exception("centos-7 components do not exist")

    if test_component == "all":
        all_components = ["baremetal", "cinder", "clients", "cloudops",
                          "common", "compute", "glance", "manila",
                          "network", "octavia", "security", "swift",
                          "tempest", "tripleo", "ui", "validation"]
    else:
        all_components = [test_component]

    if distro == "centos-8":
        component_path = "CentOS-8/component/"
        release_criteria = release
    elif distro == "rhel-8":
        component_path = "RedHat-8/component/"
        if release == "osp16-2":
            release_criteria = "rhos-16.2"
        elif release == "osp17":
            release_criteria = "rhos-17"
    # elif distro == "rhel-9":
    #     component_path = "RedHat-9/component/"

    git_url = git_base_url + component_path
    url = git_url + release_criteria + '.yaml'
    api_url, base_url = gather_basic_info_from_criteria(url)
    for component in all_components:
        commit_url = '{}component/{}/component-ci-testing/commit.yaml'.format(
                          base_url, component)
        commit_hash, distro_hash, extended_hash = fetch_hashes_from_commit_yaml(
                                                    commit_url)
        api_response = find_results_from_dlrn_repo_status(api_url,
                                                          commit_hash,
                                                          distro_hash,
                                                          extended_hash)
        (all_jobs_result_available,
         passed_jobs, failed_jobs) = conclude_results_from_dlrn(api_response)
        if 'consistent' in all_jobs_result_available:
            all_jobs_result_available.remove('consistent')
        if 'consistent' in passed_jobs:
            passed_jobs.remove('consistent')
        if 'consistent' in failed_jobs:
            failed_jobs.remove('consistent')
        jobs_in_criteria = set(find_jobs_in_component_criteria(url, component))
        jobs_which_need_pass_to_promote = jobs_in_criteria.difference(
                                            passed_jobs)
        jobs_with_no_result = jobs_in_criteria.difference(
            all_jobs_result_available)
        all_jobs = all_jobs_result_available.union(jobs_with_no_result)
        if influx:
            log_urls = latest_job_results_url(
                api_response, all_jobs_result_available)
            for job in all_jobs:
                log_url = log_urls.get(job, "N/A")
                if job in passed_jobs:
                    status = 'passed'
                elif job in failed_jobs:
                    status = 'failed'
                else:
                    status = 'pending'
                if status == 'failed':
                    failure_reason = find_failure_reason(log_url)
                else:
                    failure_reason = "N/A"
                jobs_result = {}
                jobs_result['release'] = release
                jobs_result['promote_name'] = promotion
                jobs_result['job'] = job
                jobs_result['test_hash'] = commit_hash + '_' + distro_hash[0:8]
                jobs_result['component'] = component
                jobs_result['criteria'] = job in jobs_in_criteria
                jobs_result['status'] = status
                jobs_result['logs'] = log_url
                jobs_result['failure_reason'] = failure_reason
                jobs_result['duration'] = find_job_run_time(
                    log_url)
                print(influxdb(jobs_result))
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
            console.print(f"{component} component, status={component_status}")
            print_a_set_in_table(passed_jobs, "Jobs which passed:")
            if component_status != "Green":
                print_a_set_in_table(failed_jobs, "Jobs which failed:")
                print_a_set_in_table(jobs_with_no_result,
                                     "Pending running jobs")
                print_failed_in_criteria(jobs_which_need_pass_to_promote,
                                         zb_periodic,
                                         compare_upstream,
                                         header,
                                         component)
                if component_status == "Red":
                    console.print("Logs of failing jobs:")
                    for value in log_urls.values():
                        console.print(value)
            print('\n')


full_path = os.path.dirname(os.path.abspath(__file__))
default_config_file = full_path + '/conf_ruck_rover.yaml'


@ click.command()
@ click.option("--release", default='master',
               type=click.Choice(['master', 'wallaby', 'victoria', 'ussuri',
                                  'train', 'stein', 'queens', 'osp17',
                                  'osp16-2']))
@ click.option("--distro", default='centos-8',
               type=click.Choice(['centos-8', 'centos-9', 'centos-7',
                                  'rhel-8', 'rhel-9']))
@ click.option("--component",
               type=click.Choice(["all", "baremetal", "cinder", "clients",
                                  "cloudops", "common", "compute",
                                  "glance", "manila", "network", "octavia",
                                  "security", "swift", "tempest", "tripleo",
                                  "ui", "validation"]))
@ click.option("--influx", is_flag=True, default=False)
@ click.option("--compare_upstream", is_flag=True, default=False)
@ click.option("--aggregate_hash",
               required=False,
               default="tripleo-ci-testing",
               # TO-DO w/ tripleo-get-hash
               help=("default:tripleo-ci-testing"
                     "\nexample:tripleo-ci-testing/e6/ad/e6ad..."))
@ click.option("--config_file", default=default_config_file)
def main(release,
         distro,
         influx=False,
         component=None,
         compare_upstream=False,
         aggregate_hash="tripleo-ci-testing",
         config_file=default_config_file):

    if release in ('osp16-2', 'osp17'):
        downstream_urls = 'https://url.corp.redhat.com/ruck-rover-0'
        downstream_config_file = download_file(downstream_urls)
        (zuul_url, dlrnapi_url, promoter_url,
         git_url) = load_conf_file(downstream_config_file, "downstream")
        delete_file(downstream_config_file)
    else:
        (zuul_url, dlrnapi_url, promoter_url,
         git_url) = load_conf_file(config_file, "upstream")

    if release in ('stein', 'queens'):
        distro = "centos-7"

    if component:
        track_component_promotion(release,
                                  distro,
                                  test_component=component,
                                  git_base_url=git_url,
                                  zb_periodic=zuul_url,
                                  promotion="promoted-components",
                                  compare_upstream=compare_upstream,
                                  influx=influx)
    else:
        track_integration_promotion(release,
                                    distro,
                                    dlrn_server=dlrnapi_url,
                                    promoter_base_url=promoter_url,
                                    zb_periodic=zuul_url,
                                    promotion="current-tripleo",
                                    compare_upstream=compare_upstream,
                                    influx=influx,
                                    aggregate_hash=aggregate_hash)


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter
