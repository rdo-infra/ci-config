#!/usr/bin/env python
# Copyright 2019 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import argparse
import os
import tempfile

import requests
from diskcache import Cache

ZUUL_API_BUILD = 'https://review.rdoproject.org/zuul/api/builds?job_name='

cache = Cache('/tmp/skip_cache')
cache.expire()


def main():
    parser = argparse.ArgumentParser(
        description='This will get the tempest file for fs021.')
    parser.add_argument(
        '--job_name',
        default='periodic-tripleo-ci-centos-8-ovb-1ctlr_2comp-'
        'featureset020-master',
        help="(default: %(default)s)")
    parser.add_argument(
        '--log_file',
        default='',
        help='specify the file name to be downloaded')
    parser.add_argument(
        '--tempest_dump_dir',
        default=None,
        help='specify where to create the tempest download file directory')
    args = parser.parse_args()
    get_last_build(args.job_name, args.log_file, args.tempest_dump_dir)


def get_last_build(job_name, tempest_log, tempest_dump_dir=None):
    """
     This function get the zuul job url and tempest latest log url
     and store into cache

     Parameters:
         job_name: complete job_name of the featureset
         tempest_log: tempest.html.gz or stestr.result.html file
         or stestr.results.html file
         tempest_dump_dir: temporary directory to store the tempest.html.gz
         or stestr.result.html file

     Return: tempest log url and release name
    """
    zuul_job_url = '{}{}'.format(ZUUL_API_BUILD, job_name)
    release = job_name.split('-')[-1]
    resp = requests.get(zuul_job_url)
    if resp.status_code == 200:
        zuul_log_url = resp.json()[0]['log_url']
        tempest_log_url = '{}/logs/{}'.format(zuul_log_url, tempest_log)
        if cache.get(tempest_log_url) != 200:
            resp_log = requests.get(tempest_log_url)
            if resp_log.status_code == 200:
                if not tempest_dump_dir:
                    tempest_dump_dir = tempfile.mkdtemp(prefix="skiplist-")
                download_tempest_file(tempest_log_url, tempest_dump_dir)
                cache.add(tempest_log_url, os.path.join(tempest_dump_dir))
                return (tempest_log_url, release)
            elif resp_log.status_code == 404:
                pass


def download_tempest_file(url, tempest_dump_dir):
    """
    This function will download the result file with temporary directory

    Parameters:
    url: The complete tempest log url
    tempest_dump_dir: temporary directory to store the tempest.html.gz
    or stestr.results.html file
    Return: local_filename
    """
    local_filename = url.split('/')[-1]
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(os.path.join(tempest_dump_dir, local_filename), 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    return local_filename


if __name__ == "__main__":
    main()
