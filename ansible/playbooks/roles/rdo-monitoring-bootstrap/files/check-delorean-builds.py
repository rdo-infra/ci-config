#!/usr/bin/env python
import csv
import sys
import requests
from cStringIO import StringIO
from six.moves.urllib import parse as urlparse

# Delorean build statuses
BUILD_STATUSES = ['SUCCESS', 'FAILED']

# URL to Delorean build statuses in csv format
DEFAULT_URL = 'http://trunk.rdoproject.org/centos7/current/versions.csv'

# URL to upstream project git commit
OPENSTACK_URL = "http://git.openstack.org/cgit/openstack/{0}/commit/?id={1}"
GITHUB_URL = "https://github.com/{0}/commit/{1}"


# Nagios-compatible exit codes
EXIT_CODES = {
    'OK': 0,
    'WARNING': 1,
    'CRITICAL': 2,
    'UNKNOWN': 3
}


def return_exit(status, message=None):
    """
    Helper to exit the script in a way meaningful for use in monitoring
    :param status: Can be one of 'OK', 'WARNING', 'CRITICAL, 'UNKNOWN'
    :param message: An optional message to print
    :return: exits script
    """
    # Sanity check
    if status not in EXIT_CODES:
        return_exit('UNKNOWN', 'Attempted exit through an unknown exit code')

    # If there's a message, write to stderr if not OK, otherwise stdout
    if message:
        if 'OK' not in status:
            sys.stderr.write(message)
        else:
            sys.stdout.write(message)

    sys.exit(EXIT_CODES[status])


def retrieve_report(url=DEFAULT_URL):
    """
    Helper to download the report and return a dictionary of it's values
    :param url: URL to download the csv file from
    :return: csv DictReader object
    """
    # Get the csv content into a dummy file in-memory
    report = requests.get(url).text
    report_file = StringIO(report)
    report_file.seek(0)

    # Return a parsed csv object
    csv_report = csv.DictReader(report_file)
    return csv_report


def get_commit_url(source_repo, source_sha, project):
    """
    Crafts a commit URL based on provided source_repo, source_sha and project
    :param source_repo: the source git repository
    :param source_sha: the commit built
    :param project: the project
    :return: full commit url as a string
    """
    domain = urlparse.urlsplit(source_repo).netloc
    if 'openstack' in domain:
        url = OPENSTACK_URL.format(project, source_sha)
    elif 'github' in domain:
        url = GITHUB_URL.format(project, source_sha)
    else:
        message = "Unable to parse a project URL: {0}".format(source_repo)
        return_exit('UNKNOWN', message)

    return url


if __name__ == '__main__':
    try:
        url = sys.argv[1]
    except IndexError:
        url = DEFAULT_URL
    report = retrieve_report(url=url)

    message = []
    problem = False
    for line in report:
        source_repo = line['Source Repo']
        source_sha = line['Source Sha']
        project = source_repo.split('/')[-1]
        commit = get_commit_url(source_repo, source_sha, project)
        status = line['Status']

        if "SUCCESS" not in status:
            error = "Build failure for {0} with {1}".format(project, commit)
            message.append(error)
            problem = True

    if problem:
        return_exit('CRITICAL', "\n".join(message))
    else:
        return_exit('OK', 'No build failures detected')
