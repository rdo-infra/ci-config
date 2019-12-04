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
import requests
import tempfile
from diskcache import Cache

ZUUL_API_BUILD = 'https://review.rdoproject.org/zuul/api/builds?job_name='

cache = Cache('/tmp/skip_cache')
cache.expire()

temp = tempfile.mkdtemp(prefix="skiplist")


def main():
    """
    main function
    """
    parser = argparse.ArgumentParser(
        description='This will get the tempest_file for fs021.')
    parser.add_argument(
        '--job_name',
        default='periodic-tripleo-ci-centos-7-ovb-1ctlr_2comp-'
        'featureset021-master',
        help="(default: %(default)s)",)
    parser.add_argument(
        '--log_file',
        default='',
        help='specifiy the file name to be downloaded')
    parser.add_argument(
        '--tempest_dump_dir',
        default=temp,
        help='specify where to create the tempest_download_file directory')
    args = parser.parse_args()
    get_last_build(args.job_name, args.log_file, args.tempest_dump_dir)


def get_last_build(
        job_name, tempest_log, tempest_dump_dir=temp):
    """
     featureset021 all releases job

     This function get the zuul job url and tempest lastest log url
     and store into cache

     Parameters:
         job_name: complete job_name of the featureset
         tempest_log: tempest.html.gz or stestr.result.html file
         tempest_log_url: complete job build url
         release: release name of the job

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
                download_tempest_file(tempest_log_url, tempest_dump_dir)
                cache.add(tempest_log_url, os.path.join(tempest_dump_dir))
                return (tempest_log_url, release)
            elif resp_log.status_code == 404:
                pass


def download_tempest_file(url, local_filename):
    """
    This function will download the result file with temporary directory

    Parameters:
    url: The complete tempest log url
    local_filename: Result file (tempest.html and stestr_results.html)
    Return: local_filename
    """
    local_filename = url.split('/')[-1]
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(os.path.join(temp, local_filename), 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
    return local_filename


if __name__ == "__main__":
    main()
