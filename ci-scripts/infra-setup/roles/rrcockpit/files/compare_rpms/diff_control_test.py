#!/usr/ibin/env python3

import logging
import urllib

import click
import requests
from diff_tripleo_builds import diff_builds

diff_build_fcns = diff_builds.DiffBuilds()


def get_rpm_logs(url):
    """ get the list of rpm sto compare from
    a web job log or run directly in the job
    against two files.
    Error if entry is neither a valid href or file
    location is passed.
    """

    # first test if we're using http(s) or local file
    try:
        if 'http' not in url:
            url = "file://" + url
        test_url = urllib.parse.urlparse(url)
        dict_source = dict()
        if test_url.scheme in ['http', 'https']:
            list = requests.get(url, verify=False)
            nice_list = list.content.decode('UTF-8').splitlines()
            dict_source['url'] = list.url
            dict_source['content'] = nice_list
        elif test_url.scheme == 'file':
            nice_list = open(
                test_url.path, 'r',
                encoding='UTF-8').read().split()
        return nice_list
    except Exception as e:
        print("Passed neither file not url - " + url.replace('file://', '') + e)


def diff_control_test(control_location, test_location, ignore_packages=None):
    """ diff control and test rpms using nvr format -
    minus the packages in the ignore list
    """

    full_package_diff = {}
    logging.info("\n\nThis will diff a repoquery from all enabled yum\
        repos under test, this is NOT comparing installed packages\n")

    column_list = [
        'Node',
        'Package_Name',
        'Control Package Version',
        'Test Package Version']

    control_list = get_rpm_logs(control_location)
    test_list = get_rpm_logs(test_location)
    if ignore_packages is not None:
        ignore_packages = get_rpm_logs(ignore_packages)

    control_list = diff_build_fcns.parse_list(control_list, ignore_packages)
    test_list = diff_build_fcns.parse_list(test_list, ignore_packages)

    control_list = diff_build_fcns.find_highest_version(control_list)
    test_list = diff_build_fcns.find_highest_version(test_list)

    package_diff = diff_build_fcns.diff_packages(
        control_list,
        test_list,
        not_found_message="not available")
    full_package_diff['repo_query'] = package_diff

    return [full_package_diff, column_list]


@click.command()
@click.option(
    "--control_list",
    "-c",
    required=True,
    help="a url/file that points to rpms - the control in the diff")
@click.option(
    "--test_list",
    "-t",
    required=True,
    help="a url/file that points to rpms - compared against the control list")
@click.option(
    "--ignore_list",
    "-i",
    required=False,
    help="a url/file that points to the rpms to be ignored in the comparison")
@click.option(
    "--table_location",
    "-l",
    required=False,
    help="file location to write out diff table")
def main(control_list, test_list, ignore_list, table_location):

    # set up logging
    debug_format = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
    logging.basicConfig(
            level=logging.DEBUG,
            format=debug_format,
            datefmt='%m-%d %H:%M',
            filename='debug.log',
            filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter(': %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    # diff test and control rpms
    diff_result = diff_control_test(control_list, test_list, ignore_list)
    full_package_diff = diff_result[0]
    column_list = diff_result[1]

    # output the diff table
    diff_build_fcns.display_packages_table(
        'repo_query',
        column_list,
        full_package_diff['repo_query'],
        False,
        False,
        write_table_to_file=True,
        table_file_location=table_location)


if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    main()
