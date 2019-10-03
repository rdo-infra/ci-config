# Copyright 2018 Red Hat, Inc.
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
import requests
import os
from diskcache import Cache

ZUUL_API_BUILD = 'https://review.rdoproject.org/zuul/api/builds?job_name='

cache = Cache('/tmp/skip_cache')
cache.expire()


def main():
    """
    main function
    """
    parser = argparse.ArgumentParser(
        description='This will get the tempest_file for fs021.')
    parser.add_argument(
        '--job_name',
        default='periodic-tripleo-ci-centos-7-ovb-1ctlr_2comp-featureset021-',
        help="(default: %(default)s)")
    parser.add_argument(
        '--log_file',
        default='',
        help='spacifiy the file name')
    parser.add_argument(
        '--tempest_dump_dir',
        default='/tmp/skip',
        help='tempest_dump_dir')
    args = parser.parse_args()
    get_last_build(
        args.job_name,
        args.log_file,
        args.tempest_dump_dir)


def get_last_build(job_name, tempest_log, tempest_dump_dir):
    tempest = []
    """
     Parameters:
         job_name: complete job_name
         tempest_log: tempest.html.gz or streter.html
         tempest_log_url: complete job url with tempest_log
    """
    zuul_job_url = '{}{}'.format(
            ZUUL_API_BUILD, job_name)
    resp = requests.get(zuul_job_url)
    if resp.status_code == 200:
        zuul_log_url = resp.json()[0]['log_url']
        tempest_log_url = '{}{}'.format(zuul_log_url, tempest_log)
        if tempest_log_url not in cache:
            cache.add(tempest_log_url, tempest_dump_dir)
        else:
            cache['tempest_dump_dir'] = None
    return cache['tempest_dump_dir']
    if requests.get(tempest_log_url).status_code == 200:
        if not os.path.exists(tempest_dump_dir):
            os.mkdir(tempest_dump_dir)
        file_name = download_tempest_file(
            tempest_log_url, tempest_dump_dir)
        tempest.append((file_name, job_name))
    return tempest


def download_tempest_file(url, local_dir):
    local_filename = url.split('/')[-1]
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(os.path.join(local_dir, local_filename), 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
    return local_filename


if __name__ == "__main__":
    main()
