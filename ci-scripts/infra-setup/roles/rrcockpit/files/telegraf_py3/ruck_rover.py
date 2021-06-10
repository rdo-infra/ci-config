#!/usr/bin/env python

import click
import requests
import yaml
import dlrnapi_client
from dlrnapi_client.rest import ApiException
from rich import print
from rich.table import Table
from rich.console import Console

console = Console()


def url_response_in_yaml(url):
    url_response = requests.get(url)

    return yaml.safe_load(url_response.text)


def gather_basic_info_from_criteria(url):
    url_response = requests.get(url)
    criteria_content = yaml.safe_load(url_response.text)
    api_url = criteria_content['api_url']
    base_url = criteria_content['base_url']

    return api_url, base_url


def find_jobs_in_integration_criteria(url):
    url_response = requests.get(url)
    criteria_content = yaml.safe_load(url_response.text)

    return criteria_content['promotions']['current-tripleo']['criteria']


def find_jobs_in_component_criteria(url, component):
    url_response = requests.get(url)
    criteria_content = yaml.safe_load(url_response.text)

    return criteria_content['promoted-components'][component]


def find_tripleo_ci_dlrn_hash(md5sum_url):
    return requests.get(md5sum_url).text


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
    except ApiException as e:
        print("Exception when calling DefaultApi->api_repo_status_get:"
              " %s\n" % e)
    return api_response


def conclude_results_from_dlrn(api_response):
    passed_jobs = set()
    all_jobs = set()
    for job in api_response:
        all_jobs.add(job.job_id)
        if job.success:
            passed_jobs.add(job.job_id)

    failed_jobs = all_jobs.difference(passed_jobs)

    return all_jobs, passed_jobs, failed_jobs


def latest_failing_job_results_url(api_response, failed_jobs):
    logs_failing_job = {}
    for failed_job in failed_jobs:
        latest_log = {}
        for job in api_response:
            if job.job_id == failed_job:
                latest_log[job.timestamp] = job.url
        logs_failing_job[failed_job] = latest_log[max(latest_log.keys())]

    return logs_failing_job


def print_a_set_in_table(input_set, header="Job name"):
    table = Table(show_header=True, header_style="bold")
    table.add_column(header, style="dim", width=80)
    for job in input_set:
        table.add_row(job)
    print(table)


def influxdb(missing_jobs):
    # https://docs.influxdata.com/influxdb/v2.0/reference/syntax/line-protocol/
    # missing_jobs = the measurement
    # job_type is a tag, note the space
    # rest of the values are fields in a row of data
    MISSING_INFLUXDB_LINE = ("missing_jobs,"
                             "job_type={job_type} "
                             "release={release},"
                             "name={promote_name},"
                             "job_name={job},"
                             "test_hash={test_hash},"
                             "criteria={criteria},"
                             "logs={logs},"
                             "component={component}")

    if missing_jobs['component'] is None:
        missing_jobs['job_type'] = "integration"
    else:
        missing_jobs['job_type'] = "component"
    return MISSING_INFLUXDB_LINE.format(**missing_jobs)


def track_integration_promotion(release='master',
                                promotion="current-tripleo",
                                influx=False):
    url = 'http://10.0.148.74/config/CentOS-8/' + release + '.yaml'
    api_url, base_url = gather_basic_info_from_criteria(url)
    md5sum_url = base_url + 'tripleo-ci-testing/delorean.repo.md5'
    test_hash = find_tripleo_ci_dlrn_hash(md5sum_url)
    api_response = find_results_from_dlrn_agg(api_url, test_hash)
    all_jobs, passed_jobs, failed_jobs = conclude_results_from_dlrn(
                                            api_response)
    jobs_in_critera = set(find_jobs_in_integration_criteria(url))
    jobs_which_need_pass_to_promote = jobs_in_critera.difference(passed_jobs)
    jobs_with_no_result = jobs_in_critera.difference(all_jobs)
    failing_log_urls = latest_failing_job_results_url(api_response, failed_jobs)
    # to-do, find the same information for component jobs
    if influx:
        for job in jobs_which_need_pass_to_promote:
            missing_jobs = {}
            missing_jobs['release'] = release
            missing_jobs['promote_name'] = promotion
            missing_jobs['job'] = job
            missing_jobs['test_hash'] = test_hash
            missing_jobs['component'] = None
            missing_jobs['criteria'] = "yes"
            missing_jobs['logs'] = failing_log_urls.get(job,
                                                        "Job still running")
            print(influxdb(missing_jobs))

    else:
        print(f"Hash under test: {test_hash}")
        print_a_set_in_table(passed_jobs, "Jobs which passed:")
        print_a_set_in_table(failed_jobs, "Jobs which failed:")
        print_a_set_in_table(jobs_with_no_result,
                             "Jobs whose results are awaited")
        print_a_set_in_table(jobs_which_need_pass_to_promote,
                             "Jobs which are in promotion criteria and need "
                             "pass to promote the Hash: ")
        print("Logs of jobs which are failing:-")
        for value in failing_log_urls.values():
            print(value)


def track_component_promotion(release, component,
                              promotion="promoted-components",
                              influx=False):
    """ Find the failing jobs which are blocking promotion of a component.
    :param release: The OpenStack release e.g. wallaby
    :param component:
    """

    if component == "all":
        all_components = ["baremetal", "cinder", "clients", "cloudops",
                          "common", "compute", "glance", "manila",
                          "network", "octavia", "security", "swift",
                          "tempest", "tripleo", "ui", "validation"]
    else:
        all_components = [component]

    url = 'http://10.0.148.74/config/CentOS-8/component/' + release + '.yaml'
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
        all_jobs, passed_jobs, failed_jobs = conclude_results_from_dlrn(
                                               api_response)
        jobs_in_criteria = set(find_jobs_in_component_criteria(url, component))

        jobs_which_need_pass_to_promote = jobs_in_criteria.difference(
                                            passed_jobs)
        jobs_with_no_result = jobs_in_criteria.difference(all_jobs)
        header = ("{} component jobs which need pass to promote "
                  "the hash: ").format(component)
        failing_log_urls = latest_failing_job_results_url(api_response,
                                                          failed_jobs)
        if influx:
            for job in jobs_which_need_pass_to_promote:
                missing_jobs = {}
                missing_jobs['release'] = release
                missing_jobs['promote_name'] = promotion
                missing_jobs['job'] = job
                missing_jobs['test_hash'] = commit_hash + '_' + distro_hash[0:8]
                missing_jobs['component'] = component
                missing_jobs['criteria'] = "yes"
                missing_jobs['logs'] = failing_log_urls.get(
                                         job, "Job is still running")
                print(influxdb(missing_jobs))
        else:
            if failed_jobs:
                component_status = "Red"
            elif not jobs_which_need_pass_to_promote:
                component_status = "Green"
            else:
                component_status = "Yellow"
            print(f"{component} component, status={component_status}")
            if component_status != "Green":
                print_a_set_in_table(failed_jobs, "Jobs which failed:")
                print_a_set_in_table(jobs_with_no_result,
                                     "Jobs whose results are awaited")
                print_a_set_in_table(jobs_which_need_pass_to_promote, header)
                if component_status == "Red":
                    print("Logs of failing jobs:")
                    for value in failing_log_urls.values():
                        print(value)
            print('\n')


@ click.command()
@ click.option("--release", default='master',
               type=click.Choice(['master', 'wallaby', 'victoria', 'ussuri',
                                  'train', 'osp17', 'osp16-2']))
@ click.option("--component",
               type=click.Choice(["all", "baremetal", "cinder", "clients",
                                  "cloudops", "common", "compute",
                                  "glance", "manila", "network", "octavia",
                                  "security", "swift", "tempest", "tripleo",
                                  "ui", "validation"]))
@ click.option("--influx", is_flag=True, default=False)
def main(release='master', influx=False, component=None):
    if component:
        track_component_promotion(release=release,
                                  component=component,
                                  promotion="promoted-components",
                                  influx=influx)
    else:
        track_integration_promotion(release=release,
                                    promotion="current-tripleo",
                                    influx=influx)


if __name__ == '__main__':
    main()
