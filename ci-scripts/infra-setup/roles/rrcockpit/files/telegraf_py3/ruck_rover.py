#!/usr/bin/python

import click
import requests
import yaml
import dlrnapi_client
from rich import print
from rich.table import Table
from rich.console import Console

console = Console()


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


def find_results_from_dlrn_agg(api_url, test_hash):
    api_client = dlrnapi_client.ApiClient(host=api_url)
    api_instance = dlrnapi_client.DefaultApi(api_client)
    params = dlrnapi_client.AggQuery(aggregate_hash=test_hash)
    api_response = api_instance.api_agg_status_get(params=params)

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


def print_a_set_in_table(input_set):
    table = Table(show_header=True, header_style="bold")
    table.add_column("Job name", style="dim", width=80)
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

    if missing_jobs['component'] == None:
        missing_jobs['job_type'] = "integration"
    else:
        missing_jobs['job_type'] = "component"
    return MISSING_INFLUXDB_LINE.format(**missing_jobs)


@ click.command()
@ click.option("--release", default='master',
               type=click.Choice(['master', 'wallaby', 'victoria', 'ussuri',
                                  'train', 'osp17', 'osp16-2']))
@ click.option("--promotion", default='current-tripleo',
                type=click.Choice(['current-tripleo', 'promoted-components']))
@ click.option("--influx", is_flag=True, default=False)

def main(release='master',
         promotion="current-tripleo",
         influx=False):

    url = 'http://10.0.148.74/config/CentOS-8/' + release + '.yaml'
    api_url, base_url = gather_basic_info_from_criteria(url)
    md5sum_url = base_url + 'tripleo-ci-testing/delorean.repo.md5'
    test_hash = find_tripleo_ci_dlrn_hash(md5sum_url)
    api_response = find_results_from_dlrn_agg(api_url, test_hash)
    all_jobs, passed_jobs, failed_jobs = conclude_results_from_dlrn(api_response)
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
            missing_jobs['logs'] = failing_log_urls.get(job, "Job still running")
            print(influxdb(missing_jobs))

    else:
        print(f"Hash under test: {test_hash}")
        print("Jobs which passed: \n")
        print_a_set_in_table(passed_jobs)
        print("Job which failed: \n")
        print_a_set_in_table(failed_jobs)
        print("Jobs for which result is awaited: ")
        print_a_set_in_table(jobs_with_no_result)
        print("Jobs which are in promotion criteria and need pass to promote the Hash: ")
        print_a_set_in_table(jobs_which_need_pass_to_promote)
        print("Logs of jobs which are failing:-")
        for value in failing_log_urls.values():
            print(value)


if __name__ == '__main__':
    main()
