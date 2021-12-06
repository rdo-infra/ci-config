import argparse
from configparser import ConfigParser
import os
import re
import requests
from io import BytesIO
from zipfile import ZipFile
from urllib3.exceptions import InsecureRequestWarning
import yaml
from zuulclient.api import ZuulRESTClient
from rich import print as rich_print
from rich.console import Console
from rich.table import Table

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
    content = requests.get(url, verify=False)
    f = ZipFile(BytesIO(content.content))
    unzipped_data=""
    for line in f.open(f.namelist()[0]).readlines():
        unzipped_data += line.decode('utf-8')
    return unzipped_data


def extract_jobs(text_response):
    processed_data = yaml.safe_load(text_response)
    extracted_job_name = []
    jobs = processed_data[0]['project']['check']['jobs']
    for job in jobs:
        for job_name in job.keys():
            extracted_job_name.append(job_name)
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
    z = ZuulRESTClient(url=zuul_url, auth_token=token)
    return z.autohold_list(tenant)

def add_node_on_autohold(zuul_url, token, tenant, project, job, change, ref=None, reason="debug", count=1, node_hold_expiration=86400):
    z = ZuulRESTClient(url=zuul_url, auth_token=token)
    z.autohold(tenant, project, job, change, ref, reason, count, node_hold_expiration)

def remove_node_from_hold(zuul_url, token, id, tenant):
    z = ZuulRESTClient(url=zuul_url, auth_token=token)
    z.autohold_delete(id, tenant)

def print_jobs_on_hold(input_list):
    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", width=10)
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

def main(patch_url, reason, confirm, delete, status):
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

    home_dir = os.path.expanduser('~')
    config_parser = ConfigParser()
    config_parser.read(home_dir+'/.config/zuul/client.conf')
    token=config_parser[config]['auth_token']
    tenant=config_parser[config]['tenant']
    url=config_parser[config]['url']

    if status:
        nodes_on_hold_list = check_autohold_list(url, token, tenant)
        print_jobs_on_hold(nodes_on_hold_list)

    if not delete and not status:
        fetched_jobs = extract_jobs(data)
        for job in fetched_jobs:
            print(f"Will add job: {job} on hold for project: {project_name} and change: {patch_id} in {gerrit}")
            if confirm:
                add_node_on_autohold(zuul_url=url, token=token, tenant=tenant, project=project_name, job=job, change=patch_id, ref=None, reason=reason, count=1, node_hold_expiration=86400)
            else:
                print("Please pass -c to confirm")

    if delete:
        nodes_on_hold_list = check_autohold_list(url, token, tenant)
        for item in nodes_on_hold_list:
            if patch_id in item['ref_filter']:
                print(f"Removing {item['job']} from hold for patch: {patch_id} ")
                remove_node_from_hold(url, token, id=item['id'], tenant=tenant)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Script to add a node on hold for debug")
    parser.add_argument('patch_url')
    parser.add_argument('-r',
                        '--reason',
                        default='debug',
                        help="Add a reason for putting node on hold, Typically we include our name, ex: ysandeep_debug")
    parser.add_argument('-c',
                        '--confirm',
                        action='store_true',
                        help="Confirm that you want to use ")
    parser.add_argument('-d',
                        '--delete',
                        action='store_true',
                        help="Remove/delete a node from node")
    parser.add_argument('-s',
                        '--status',
                        action='store_true',
                        help="Status of which all nodes are under hold")
    args = parser.parse_args()
    main(args.patch_url, args.reason, args.confirm, args.delete, args.status)





