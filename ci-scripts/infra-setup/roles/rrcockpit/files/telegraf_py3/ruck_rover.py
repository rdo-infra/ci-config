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


def print_a_set_in_table(input_set):
    table = Table(show_header=True, header_style="bold")
    table.add_column("Job name", style="dim", width=80)
    for job in input_set:
        table.add_row(job)
    print(table)


@ click.command()
@ click.option("--release", default='master',
               type=click.Choice(['master', 'wallaby', 'victoria', 'ussuri',
                                  'train', 'osp17', 'osp16-2']))
def main(release='master'):
    url = 'http://10.0.148.74/config/CentOS-8/' + release + '.yaml'
    api_url, base_url = gather_basic_info_from_criteria(url)
    md5sum_url = base_url + 'tripleo-ci-testing/delorean.repo.md5'

    test_hash = find_tripleo_ci_dlrn_hash(md5sum_url)
    print(f"Hash under test: {test_hash}")
    api_response = find_results_from_dlrn_agg(api_url, test_hash)
    all_jobs, passed_jobs, failed_jobs = conclude_results_from_dlrn(api_response)

    print("Jobs which passed: \n")
    print_a_set_in_table(passed_jobs)
    print("Job which failed: \n")
    print_a_set_in_table(failed_jobs)

    jobs_in_critera = set(find_jobs_in_integration_criteria(url))
    jobs_which_need_pass_to_promote = jobs_in_critera.difference(passed_jobs)
    jobs_with_no_result = jobs_in_critera.difference(all_jobs)

    print("Jobs with no result in dlrn for this hash: ")
    print_a_set_in_table(jobs_with_no_result)
    print("Jobs which are in promotion criteria and need pass to promote the Hash: ")
    print_a_set_in_table(jobs_which_need_pass_to_promote)


if __name__ == '__main__':
    main()
