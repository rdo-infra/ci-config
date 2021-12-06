#!/usr/bin/env python

import argparse
from configparser import ConfigParser
import os
import re
import requests
from io import BytesIO
from zipfile import ZipFile
import yaml
from zuulclient.api import ZuulRESTClient
from rich.console import Console
from rich.table import Table
from urllib3.exceptions import InsecureRequestWarning


console = Console()


def fetch_change_id(patch_url):
    """ Fetches change id from a gerrit patch URL
    :param patch_url: Gerrit patch URL in string format
    :returns: patch id in a string format
    """
    try:
        patch_id = re.search("\d+", patch_url).group(0)
    except AttributeError as err:
        err.args = (f"No id found in the provided url {patch_url}",)
        raise

    return patch_id


def fetch_patchset_number(patch_url):
    """ Fetches patchset number from a gerrit URL
    :param patch_url: Gerrit URL in string format
    :returns: patch patchset_number in a string format
    """
    try:
        patchset_number = re.findall("\d+", patch_url)[1]
    except IndexError as err:
        err.args = (f"No patchset number found in the provided url {patch_url}",)
        raise

    return patchset_number


def fetch_project_name(patch_url):
    """ Fetches project name from a URL
    :param patch_url: URL in string format
    :returns: project name in a string format
    """
    splitted_patch_url = [x for x in patch_url.split('/') if x]

    add_index = 1
    for name in ['openstack', 'rdo-infra']:
        if name in splitted_patch_url:
            add_index = 2

    if 'c' in splitted_patch_url:
        try:
            project_name = splitted_patch_url[splitted_patch_url.index('c') + add_index]
        except IndexError as err:
            err.args = (f"Unable to find project in the provided url {patch_url}",)
            raise

    return project_name


def gerrit_check(patch_url):
    """ Check if patch belongs to upstream/rdo/downstream gerrit,
    :param patch_url: Gerrit URL in a string format
    :returns gerrit: return string i.e 'upstream'/'rdo'/'downstream'
    """
    if 'redhat' in patch_url:
        return 'downstream'
    elif 'review.rdoproject.org' in patch_url:
        return 'rdo'
    elif 'review.opendev.org' in patch_url:
        return 'upstream'
    else:
        raise Exception(f'Unknown gerrit patch link provided: {patch_url}')


def fetch_file_name(patch_url):
    """ fetch zuul file name from a gerrit URL
    :param patch_url: Gerrit patch URL in a string format
    :returns file_name: string
    """
    splitted_patch_url = [x for x in patch_url.split('/') if x]
    if 'yaml' in splitted_patch_url[-1]:
        return splitted_patch_url[-1]
    else:
        raise Exception(f'No zuul yaml provided in : {patch_url}')


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


# https://stackoverflow.com/questions/5710867/downloading-and-unzipping-a-zip-file-without-writing-to-disk
def download_and_unzip_without_writing_to_disk(url):
    try:
        requests.packages.urllib3.disable_warnings(
            category=InsecureRequestWarning)
        content = requests.get(url, verify=False)
        content.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err)
    except requests.exceptions.RequestException as error:
        raise SystemExit(error)
    f = ZipFile(BytesIO(content.content))
    unzipped_data=""
    for line in f.open(f.namelist()[0]).readlines():
        unzipped_data += line.decode('utf-8')
    return unzipped_data


def extract_jobs(text_response):
    processed_data = yaml.safe_load(text_response)
    for i, j in enumerate(processed_data):
        if 'project' in j.keys():
            project_index = i

    extracted_job_name = []
    jobs = processed_data[project_index]['project']['check']['jobs']
    for job in jobs:
        if isinstance(job, dict):
            for job_name in job.keys():
                extracted_job_name.append(job_name)
        elif isinstance(job, str):
            extracted_job_name.append(job)

    return extracted_job_name


def convert_patch_url_to_download_url(patch_url, patch_id, project_name, patchset_number, file_name):
    """ Convert gerrit patch URL to URl from where
    we can download the patch
    :param patch_url: URL in string format
    :returns: download_patch_url in a string format
    """
    if 'c/' in patch_url:
        url_first_part = patch_url.split('c/')[0]
    else:
        raise Exception(f"Doesn't looks like a proper gerrit patch URL, we split the url on 'c/'")
    second_part_url = f"changes/{project_name}~{patch_id}/revisions/{patchset_number}/files/{file_name}/download"

    return url_first_part + second_part_url


def check_autohold_list(zuul_url, token, tenant):
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
    z = ZuulRESTClient(url=zuul_url, auth_token=token)
    return z.autohold_list(tenant)


def add_node_on_autohold(zuul_url, token, tenant, project, job, change, ref=None, reason="debug", count=1, node_hold_expiration=86400):
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
    z = ZuulRESTClient(url=zuul_url, auth_token=token)
    z.autohold(tenant, project, job, change, ref, reason, count, node_hold_expiration)


def remove_node_from_hold(zuul_url, token, id, tenant):
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
    z = ZuulRESTClient(url=zuul_url, auth_token=token)
    z.autohold_delete(id, tenant)


def print_jobs_on_hold(input_list):
    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", width=15)
    table.add_column("Tenant", width=15)
    table.add_column("Project", width=35)
    table.add_column("Job", width=75)
    table.add_column("ref_filter", width=25)
    table.add_column("Reason", width=30)
    if input_list:
        for item in input_list:
            table.add_row(item['id'],
                         item['tenant'],
                         item['project'],
                         item['job'],
                         item['ref_filter'],
                         item['reason'])
    console.print(table)


def extract_credentials_from_config(config):
    home_dir = os.path.expanduser('~')
    config_parser = ConfigParser()
    config_parser.read(home_dir+'/.config/zuul/client.conf')
    token=config_parser[config]['auth_token']
    tenant=config_parser[config]['tenant']
    url=config_parser[config]['url']
    return url, token, tenant


def status(input):
    if input in ['rdo', 'rdoproject.org']:
        config = 'rdoproject.org'
    elif input in ['downstream', 'tripleo-ci-internal']:
        config = 'tripleo-ci-internal'
    else:
        config = input
    url, token, tenant = extract_credentials_from_config(config)
    nodes_on_hold_list = check_autohold_list(url, token, tenant)
    print_jobs_on_hold(nodes_on_hold_list)


def add_node_workflow(patch_url, reason, confirm, passed_job_name=""):
    patch_id = fetch_change_id(patch_url)
    patchset_number = fetch_patchset_number(patch_url)
    project_name = fetch_project_name(patch_url)
    file_name = fetch_file_name(patch_url)
    download_patch_url = convert_patch_url_to_download_url(patch_url, patch_id, project_name, patchset_number, file_name)
    gerrit = gerrit_check(patch_url)

    if gerrit == 'rdo':
        data = web_scrape(download_patch_url)
        config = 'rdoproject.org'
    elif gerrit == 'downstream':
        data = download_and_unzip_without_writing_to_disk(download_patch_url)
        config = 'tripleo-ci-internal'

    url, token, tenant = extract_credentials_from_config(config)
    fetched_jobs = extract_jobs(data)
    if len(fetched_jobs)==0:
        print(f"{patch_id} zuul layout didn't contains any job name")
    elif len(fetched_jobs)==1:
        for job in fetched_jobs:
            if confirm:
                print(f"Adding job: {job} on hold for project: {project_name} and change: {patch_id} in {gerrit}")
                add_node_on_autohold(zuul_url=url, token=token, tenant=tenant, project=project_name, job=job, change=patch_id, ref=None, reason=reason, count=1, node_hold_expiration=86400)
            else:
                print(f"Will add job: {job} on hold for project: {project_name} and change: {patch_id} in {gerrit}")
                print("Please pass -c to confirm")
    else:
        if not passed_job_name:
            print(f"Patch: {patch_url} contains more than 1 job, please pass --job_name <name of job> to tell which job you want to hold")
            for i in fetched_jobs:
                print(i)
            return
        if confirm:
            print(f"Adding job: {passed_job_name} on hold for project: {project_name} and change: {patch_id} in {gerrit}")
            add_node_on_autohold(zuul_url=url, token=token, tenant=tenant, project=project_name, job=passed_job_name, change=patch_id, ref=None, reason=reason, count=1, node_hold_expiration=86400)
        else:
            print(f"Will add job: {passed_job_name} on hold for project: {project_name} and change: {patch_id} in {gerrit}")
            print("Please pass -c to confirm")


def delete_node_workflow_using_url(patch_url, confirm):
    gerrit = gerrit_check(patch_url)
    patch_id = fetch_change_id(patch_url)
    if gerrit == 'rdo':
        config = 'rdoproject.org'
    elif gerrit == 'downstream':
        config = 'tripleo-ci-internal'
    url, token, tenant = extract_credentials_from_config(config)
    nodes_on_hold_list = check_autohold_list(url, token, tenant)
    for item in nodes_on_hold_list:
        if patch_id in item['ref_filter']:
            if confirm:
                print(f"Removing {item['job']} from hold for patch: {patch_id} ")
                remove_node_from_hold(url, token, id=item['id'], tenant=tenant)
            else:
                print(f"Will remove {item['job']} from hold for patch: {patch_id} ")
                print("Please pass -c to confirm")


def delete_node_workflow_using_job_id(job_id, gerrit, confirm):
    if gerrit in ['rdo', 'rdoproject.org']:
        config = 'rdoproject.org'
    elif gerrit in ['downstream', 'tripleo-ci-internal']:
        config = 'tripleo-ci-internal'
    else:
        config = gerrit
    url, token, tenant = extract_credentials_from_config(config)
    nodes_on_hold_list = check_autohold_list(url, token, tenant)
    for item in nodes_on_hold_list:
        if job_id == item['id']:
            if confirm:
                print(f"Removing {item['job']} from hold")
                remove_node_from_hold(url, token, id=item['id'], tenant=tenant)
            else:
                print(f"Will remove {item['job']} from hold")
                print("Please pass -c to confirm")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Script to add a node on hold for debug")
    parser.add_argument('-a',
                        '--add_using_patch',
                        default='',
                        help="Pass the Gerrit patch url to zuul layout file, We add hold for jobs found in layout")
    parser.add_argument('-r',
                        '--reason',
                        default='debug',
                        help="Add a reason for putting node on hold, Typically we include our name, ex: ysandeep_debug")
    parser.add_argument('-c',
                        '--confirm',
                        action='store_true',
                        help="Confirm add/delete action")
    parser.add_argument('-d',
                        '--delete_using_url',
                        default='',
                        help="Gerrit patch url to zuul layout file, We remove hold for jobs found in layout")
    parser.add_argument('--job_name',
                        default='',
                        help="Incase zuul layout contains more than 1 job, pass the job name with --job_name")
    parser.add_argument('--delete_with_id',
                        default='',
                        help="Remove/delete a node from node using id, You will find the id on running --list command")
    parser.add_argument('-l',
                        '--list',
                        action='store_true',
                        help="List all nodes which are under hold")
    parser.add_argument('--config',
                        default='',
                        help="config to use: rdo or downstream or other(should be mentioned in client.conf) rdo/downstream are shortcuts for CI team.")
    args = parser.parse_args()
    #main(args.patch, args.reason, args.confirm, args.delete, args.status)
    if args.list:
        if args.config:
            status(args.config)
        else:
            print("Please pass --config i.e rdo or downstream to mention where to check status of hold nodes")
    elif args.add_using_patch:
        add_node_workflow(args.add_using_patch, args.reason, args.confirm, args.job_name)
    elif args.delete_using_url:
        delete_node_workflow_using_url(args.delete_using_url, args.confirm)
    elif args.delete_with_id:
        if args.config:
            delete_node_workflow_using_job_id(args.delete_with_id, args.config, args.confirm)
        else:
            print("Please pass --config i.e rdo or downstream to mention where to remove the hold nodes.")


