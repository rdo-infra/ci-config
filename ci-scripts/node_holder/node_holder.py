#!/usr/bin/env python

"""
This script automates the steps of adding/removing a node on hold
and also reduces the chances of error.

Features of this script:-

A) Autodetect job name, project name, change id and config(patch belong to
   rdo/downstream/any other tenant config).
B) Use zuulclient python api instead of using cli commands.

"""


import argparse
import getpass
import os
import re
from configparser import ConfigParser
from io import BytesIO
from zipfile import ZipFile

import requests
import yaml
from rich.console import Console
from rich.table import Table
from urllib3.exceptions import InsecureRequestWarning
from zuulclient.api import ZuulRESTClient

console = Console()


def fetch_change_id(patch_url):
    """ Fetches change id from a gerrit patch URL
    :param patch_url: Gerrit patch URL in string format
    :returns: patch id in a string format
    """
    try:
        patch_id = re.search(r"\d+", patch_url).group(0)
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
        patchset_number = re.findall(r"\d+", patch_url)[1]
    except IndexError as err:
        err.args = (f"No patchset number found in the provided url {patch_url}")
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
            project_name = splitted_patch_url[
                splitted_patch_url.index('c') + add_index]
        except IndexError as err:
            err.args = (f"Unable to find project in the url: {patch_url}")
            raise

    return project_name


def gerrit_check(patch_url):
    """ Check if patch belongs to upstream/rdo/downstream gerrit,
    :param patch_url: Gerrit URL in a string format
    :returns gerrit: return string i.e 'upstream'/'rdo'/'downstream'
    """
    if 'redhat' in patch_url:
        return 'downstream'
    if 'review.rdoproject.org' in patch_url:
        return 'rdo'
    if 'review.opendev.org' in patch_url:
        print("We don't have ability to hold a node in upstream")
        return 'upstream'
    raise Exception(f'Unknown gerrit patch link provided: {patch_url}')


def fetch_file_name(patch_url):
    """ fetch zuul file name from a gerrit URL
    :param patch_url: Gerrit patch URL in a string format
    :returns file_name: string
    """
    splitted_patch_url = [x for x in patch_url.split('/') if x]
    if 'yaml' in splitted_patch_url[-1]:
        if splitted_patch_url[-2] == 'zuul.d':
            return splitted_patch_url[-2] + '%2F' + splitted_patch_url[-1]
        return splitted_patch_url[-1]
    raise Exception(f'No zuul yaml provided in : {patch_url}')


def web_scrape(url):
    """ Scrap zuul layout yaml from a url
    :param url: Url to download content from
    :returns response: string containing job names
    """
    requests.packages.urllib3.disable_warnings(
        category=InsecureRequestWarning)
    response = requests.get(url, verify=False)
    response.raise_for_status()

    return response.text


def download_and_unzip_without_writing_to_disk(url):
    """ download and unzip a zipped zuul layout yaml file
    :param url: Url to download content from.
    :returns response: string containing job names
    """
    requests.packages.urllib3.disable_warnings(
        category=InsecureRequestWarning)
    content = requests.get(url, verify=False)
    content.raise_for_status()

    with ZipFile(BytesIO(content.content)) as my_zip_file:
        unzipped_data = ""
        with my_zip_file.open(my_zip_file.namelist()[0]) as unzipped_file:
            for line in unzipped_file.readlines():
                unzipped_data += line.decode('utf-8')

    return unzipped_data


def extract_jobs(text_response):
    """ Extract jobs name in a list from string
    :param url: text_response: string containing jobs name in multiple lines
    :returns: extracted_job_name: List containing jobs name
    """
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


def convert_patch_url_to_download_url(patch_url, patch_id,
                                      project_name, patchset_number,
                                      file_name):
    """ Convert gerrit patch URL to URl from where
    we can download the patch
    :param patch_url: URL in string format
    :returns: download_patch_url in a string format
    """
    if 'c/' in patch_url:
        url_first_part = patch_url.split('c/')[0]
    else:
        raise Exception("Doesn't looks like a proper gerrit patch URL: "
                        "we split the url on 'c/'")
    second_part_url = (
        f"changes/{project_name}~{patch_id}/revisions/"
        f"{patchset_number}/files/{file_name}/download")

    return url_first_part + second_part_url


def check_autohold_list(zuul_url, token, tenant):
    """ Return list of jobs which are currently on hold.
    :param zuul_url str: Zuul url
    :param token str: Token id
    :param tenant str: Tenant name
    :returns list: list of jobs in hold status in string format.
    """
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
    client = ZuulRESTClient(url=zuul_url, auth_token=token)

    return client.autohold_list(tenant)


def add_node_on_autohold(zuul_url, token, tenant, project, job,
                         change, ref=None, reason='debug',
                         count=1, node_hold_expiration=86400):
    """ Add a job on hold for debugging
    :param zuul_url str: Zuul url
    :param token str: Token id
    :param tenant str: Tenant name
    :param project str: Project name
    :param job str: job name
    :param ref str: git ref to hold nodes for(default: None)
    :param reason str: reason for the hold ( default: 'debug')
    :param count int: number of job runs (default: 1)
    :param node_hold_expiration int: how long in seconds should the node set
     be in HOLD status (default: 86400)
    :returns None: Add a job on hold.
    """
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
    client = ZuulRESTClient(url=zuul_url, auth_token=token)
    client.autohold(tenant, project, job, change,
                    ref, reason, count, node_hold_expiration)


def remove_node_from_hold(zuul_url, token, tenant, job_id):
    """ Remove a node from hold
    :param zuul_url str: Zuul url
    :param token str: Token id
    :param tenant str: Tenant name
    :param job_id str: job id
    :returns None: Remove the node from hold for provided job_id.
    """
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
    client = ZuulRESTClient(url=zuul_url, auth_token=token)
    client.autohold_delete(job_id, tenant)


def print_jobs_on_hold(input_list):
    """ Print formatter to print jobs which are in hold status in a
    table format.
    :param input_list: list of jobs in hold status in string format.
    :returns None.
    """
    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", width=15)
    table.add_column("Tenant", width=15)
    table.add_column("Project", width=35)
    table.add_column("Job", width=75)
    table.add_column("ref_filter", width=25)
    table.add_column("Reason", width=30)
    if input_list:
        for item in input_list:
            table.add_row(item['id'], item['tenant'], item['project'],
                          item['job'], item['ref_filter'], item['reason'])
    console.print(table)


def extract_credentials_from_config(config):
    """ Extract crendentials for a particular config option from
    config file $HOME/.config/zuul/client.conf
    :param config str: A particular config section name for which
     you want to fetch credentials.
    :returns url, token, tenant.
    """
    home_dir = os.path.expanduser('~')
    config_parser = ConfigParser()
    conf_file = home_dir + '/.config/zuul/client.conf'
    try:
        f = open(conf_file)
        f.close()
    except FileNotFoundError as err:
        custom_message = (f"Configuration file {conf_file} not found "
                          "You need to create a configuration file "
                          "with url/tenant/auth_token, Please reach"
                          "out to infra for these details.")
        raise FileNotFoundError(custom_message) from err
    else:
        config_parser.read(conf_file)
        token = config_parser[config]['auth_token']
        tenant = config_parser[config]['tenant']
        url = config_parser[config]['url']
        return url, token, tenant


def status(input_config):
    """ Check status of jobs which are on hold and print them.
    :param input_config str: 'rdo/downstream' for which you want
     to check status.
    :returns None.
    """
    if input_config in ['rdo', 'rdoproject.org']:
        config = 'rdoproject.org'
    elif input_config in ['downstream', 'tripleo-ci-internal']:
        config = 'tripleo-ci-internal'
    else:
        config = input_config
    url, token, tenant = extract_credentials_from_config(config)
    nodes_on_hold_list = check_autohold_list(url, token, tenant)
    print_jobs_on_hold(nodes_on_hold_list)


def add_node_workflow(patch_url, reason, confirm,
                      passed_job_name="", node_hold_expiration=86400):
    """ This function manages the entire flow of adding a node on hold.
    :param patch_url str: URL in string format to zuul layout file.
    :param reason str: reason for the hold ( default: 'debug')
    :param confirm bool: Confirm action to add a node on hold
    :param passed_job_name str: If more than one job found in zuul layout,
     we need to passed_job_name to select which job we add on hold.
     (default: '', optional)
    :param node_hold_expiration int: how long in seconds should the node set
     be in HOLD status (default: 86400).
    :return None: Add a node on hold.
    """
    patch_id = fetch_change_id(patch_url)
    patchset_number = fetch_patchset_number(patch_url)
    project_name = fetch_project_name(patch_url)
    file_name = fetch_file_name(patch_url)
    download_patch_url = convert_patch_url_to_download_url(
        patch_url, patch_id, project_name, patchset_number, file_name)
    gerrit = gerrit_check(patch_url)

    if gerrit == 'rdo':
        data = web_scrape(download_patch_url)
        config = 'rdoproject.org'
    elif gerrit == 'downstream':
        data = download_and_unzip_without_writing_to_disk(download_patch_url)
        config = 'tripleo-ci-internal'

    url, token, tenant = extract_credentials_from_config(config)
    fetched_jobs = extract_jobs(data)
    if len(fetched_jobs) == 0:
        print(f"{patch_id} zuul layout didn't contains any job name")
    elif len(fetched_jobs) == 1:
        for job in fetched_jobs:
            if confirm:
                print(
                    (f"Adding job: {job} on hold for project: {project_name}"
                     f" and change: {patch_id} in {gerrit}"))
                add_node_on_autohold(zuul_url=url, token=token,
                                     tenant=tenant, project=project_name,
                                     job=job, change=patch_id, ref=None,
                                     reason=reason, count=1,
                                     node_hold_expiration=node_hold_expiration)
            else:
                print(
                    (f"Will add job: {job} on hold for project:"
                     f"{project_name} and change: {patch_id} in {gerrit}"))
                print("Please pass -c to confirm")
    else:
        if not passed_job_name:
            print(
                (f"Patch: {patch_url} contains more than 1 job, please pass "
                 f"--job_name <name of job> which job you want to hold"))
            for item in fetched_jobs:
                print(item)
            return
        if confirm:
            print(
                (f"Adding job: {passed_job_name} on hold for project:"
                 f" {project_name} and change: {patch_id} in {gerrit}"))
            add_node_on_autohold(zuul_url=url, token=token,
                                 tenant=tenant, project=project_name,
                                 job=passed_job_name, change=patch_id,
                                 ref=None, reason=reason, count=1,
                                 node_hold_expiration=node_hold_expiration)
        else:
            print(
                (f"Will add job: {passed_job_name} on hold for project:"
                 f"{project_name} and change: {patch_id} in {gerrit}"))
            print("Please pass -c to confirm")


def delete_node_workflow_using_url(patch_url, confirm):
    """ This function manages the entire flow of deleting a node from hold
    using gerrit patch
    :param patch_url str: URL to gerrit patch.
    :param confirm bool: Confirm action to delete a node on hold
    :returns None: Delete a node from hold
    """
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
                print(f"Removing hold for job {item['job']} patch: {patch_id}")
                remove_node_from_hold(url, token, tenant=tenant,
                                      job_id=item['id'])
            else:
                print(f"Will remove {item['job']} from hold for patch:"
                      f" {patch_id} ")
                print("Please pass -c to confirm")


def delete_node_workflow_using_job_id(job_id, gerrit, confirm):
    """ This function manages the entire flow of deleting a node from hold
    using job id.
    :param job_id str: Job id.
    :param gettit str: 'rdo/downstream/<other>' from where you want to remove
     a node from hold.
    :param confirm bool: Confirm action to delete a node on hold
    :returns None: Delete a node from hold
    """
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
                remove_node_from_hold(url, token, tenant=tenant,
                                      job_id=item['id'])
            else:
                print(f"Will remove {item['job']} from hold")
                print("Please pass -c to confirm")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Script to add a node on hold for debug, this script"
                    " assumes you have a config file(containing: url"
                    "/tenant/auth_token) at $HOME/.config/zuul/client.conf."
                    " You need to request someone from infra to create a"
                    " token for you.")
    parser.add_argument('-a',
                        '--add_using_autodetect',
                        default='',
                        help=" Pass the gerrit patch url to zuul layout file,"
                             " If a single job found in layout we delete that"
                             " job from hold. If more than one job found in"
                             " layout, we need to pass the job name we are"
                             " trying to remove from hold with --job_name")
    parser.add_argument('-r',
                        '--reason',
                        default=getpass.getuser(),
                        help="Add a reason for putting node on hold,"
                             "Default: local user $USERNAME from where"
                             "you are running the script")
    parser.add_argument('-c',
                        '--confirm',
                        action='store_true',
                        help="Confirm add/delete action")
    parser.add_argument('-d',
                        '--delete_using_autodetect',
                        default='',
                        help="Remove/delete autohold query using gerrit"
                             " patch url,  Pass the gerrit patch url as"
                             " parameter.")
    parser.add_argument('--job_name',
                        default='',
                        help="Incase zuul layout contains more than 1 job,"
                             " pass the job name with --job_name")
    parser.add_argument('--delete_with_id',
                        default='',
                        help="Remove/delete autohold query using job id"
                             "You will find the id by running --list command")
    parser.add_argument('-l',
                        '--list',
                        action='store_true',
                        help="List all nodes which are under hold")
    parser.add_argument('--node_hold_expiration',
                        default=86400,
                        help="how long in seconds should the node set be in"
                             " HOLD status, default 86400(1 day)")
    parser.add_argument('--config',
                        default='',
                        help="config to use: rdo or downstream or other"
                             "(should be mentioned in client.conf)"
                             " rdo/downstream are shortcuts for CI team.")
    args = parser.parse_args()
    if args.list:
        if args.config:
            status(args.config)
        else:
            print("Please pass --config i.e rdo or downstream to mention"
                  " where to check status of hold nodes")
    elif args.add_using_autodetect:
        add_node_workflow(args.add_using_autodetect, args.reason,
                          args.confirm, args.job_name,
                          args.node_hold_expiration)
    elif args.delete_using_autodetect:
        delete_node_workflow_using_url(args.delete_using_autodetect,
                                       args.confirm)
    elif args.delete_with_id:
        if args.config:
            delete_node_workflow_using_job_id(args.delete_with_id,
                                              args.config, args.confirm)
        else:
            print("Please pass --config i.e rdo or downstream to mention"
                  " where to remove the hold nodes.")
