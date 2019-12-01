#!/usr/bin/env python

# Thi script takes a DockerHub namespace and searches the repos
# matching the filter string for tags.
# It lists repos with tags and deletes them.

import argparse
import base64
import json
import os
import sys

try:
    from urllib.parse import urlencode, urlparse
    from urllib.request import (
        urlopen, Request, unquote, build_opener, HTTPHandler)
    from urllib.error import HTTPError
except ImportError:
    from urllib import urlencode, unquote
    from urlparse import urlparse
    from urllib2 import urlopen, Request, HTTPError
    from urllib2 import build_opener, HTTPHandler


def login_dockerhub():
    ''' login to DockerHub using sourced
        creds file
    '''

    url = 'https://hub.docker.com/v2/users/login/'
    data = urlencode({
        'username': os.environ['DOCKERHUB_USERNAME'],
        'password': os.environ['DOCKERHUB_PASSWORD']}
    ).encode("utf-8")
    req = Request(url, data)
    response = urlopen(req)

    try:
        body = response.read().decode('utf-8')
        body = json.loads(body)
        token = body['token']
        return token
    except:
        print("Error obtaining token")
        sys.exit(1)


def return_url_body(url_string):
    ''' return body of url request '''

    token = login_dockerhub()

    headers = {
        'Authorization': 'JWT %s' % token
    }
    request = Request(url=url_string, headers=headers)
    response = urlopen(request)
    body = response.read().decode('utf-8')
    body = json.loads(body)

    return body


def return_filter_repos_in_namespace(namespace, filter_string):
    ''' return list of repos in a namespace matching the
        filter_string '''

    another_page = True
    i = 1
    compl_repos_list = []
    repos_list  = []
    while another_page:
        url_string = ("https://hub.docker.com/v2/repositories/"
             "%s/?page=%d" % (namespace, i))
        body = return_url_body(url_string)
        print(url_string)

        if filter_string+"-" in json.dumps(body):
            results_range = list(range(0, len(body['results'])))
            repos_list = [body['results'][r]['name']
                for r in results_range
                if 'rhel' in body['results'][r]['name']]
            print(repos_list)

        if body['next'] is None:
            another_page = False
        else:
            another_page = True
            i += 1

        compl_repos_list = compl_repos_list + repos_list

    return compl_repos_list


def return_tags_in_repo(namespace, repo):
    ''' returns list of tags in a namespace/repo '''

    url_string = ("https://hub.docker.com/v2/repositories"
         "/%s/%s/tags/?page_size=1024" % (namespace, repo))
    body = return_url_body(url_string)

    results_range = list(range(0, len(body['results'])))
    tags_list = [body['results'][i]['name'] for i in results_range]
    print(tags_list)

    return tags_list


def delete_repo_with_tag(namespace, repo, tag):
    ''' Deletes repo(image) with specified namespace/repo/tag '''

    token = login_dockerhub()

    url = ("https://hub.docker.com/v2/repositories"
         "/%s/%s/tags/%s/" % (namespace, repo, tag))
    headers = {
        'Authorization': 'JWT %s' % token
    }
    request = Request(url=url, headers=headers)
    # https://github.com/appscodelabs/libbuild/blob/master/docker.py#L31
    # Uncomment to delete
    #request.get_method = lambda: 'DELETE'
    try:
        opener = build_opener(HTTPHandler)
        #opener.open(request)
        print('%s/%s:%s deleted successfully.' % (namespace, repo, tag))
    except HTTPError as err:
        print("Failed to delete tag %s, exiting." % err)
        sys.exit(1)


def main():

    # initiate the parser
    parser = argparse.ArgumentParser(
             description='Pass a namespace and filter string for repos.')
    parser.add_argument("--namespace", "-n", help="namespace containing repos")
    parser.add_argument("--filter_string", "-f", help="string to filter repos")
    # read arguments from the command line
    args = parser.parse_args()

    namespace = args.namespace
    filter_string = args.filter_string

    # Get a list of repos within a namespace matching a filter string
    filtered_repos = return_filter_repos_in_namespace(namespace, filter_string)
    # For each repo, return the list of tags
    for repo in filtered_repos:
        tags_list = return_tags_in_repo(namespace, repo)
        # For each tag, delete the repo with that tag
        for tag in tags_list:
            delete_repo_with_tag(namespace, repo, tag)


if __name__ == "__main__":
    main()
