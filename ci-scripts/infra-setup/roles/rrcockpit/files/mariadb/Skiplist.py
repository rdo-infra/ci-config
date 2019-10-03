# Copyright 2016 Red Hat, Inc.
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
import Tempest_file_downloader
import Tempest_html_json
import glob
import os
from diskcache import Cache


parse_result = []
previously_processed_files = [
    'tempest.html.gz-master',
    'tempest.html.gz-stein']
recent_files = []
cache = Cache('/tmp/skip/')
cache.expire()


def get_diff():
    """
    This function gives the difference of previously proccessed files and
    recent files
    """
    return list(set(previously_processed_files) - set(recent_files))


def get_files():
    """
    This function gives the result of all the files parsed from html to json
    """
    Tempest_file_downloader.get_last_build()
    with Cache('/tmp/skip') as open:
        list_of_files = glob.glob('/tmp/skip/*.gz')
        recent_files = max(list_of_files, key=os.path.getctime)
        if not get_diff():
            pass
        else:
            previously_processed_files.extend(get_diff())
            for file in get_diff():
                parse_result.append(Tempest_html_json.main())

if __name__ == "__main__":
    get_files()
