#!/usr/bin/env python
#   Copyright Red Hat, Inc. All Rights Reserved.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

# This script is a Sensu handler meant to accept data from Sensu as stdin in
# order to post events to Errbot.

import argparse
import requests
import sys

try:
    import simplejson as json
except ImportError:
    import json


def post(payload, endpoint):
    r = requests.post(endpoint, data=json.dumps(payload))
    return r.status_code

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--endpoint',
                        required=True,
                        help='API endpoint to post events to.')

    args = parser.parse_args()
    try:
        data = json.load(sys.stdin)
    except Exception as e:
        print("Unable to parse JSON: {0}".format(str(e)))
        sys.exit(1)

    try:
        response = post(data, args.endpoint)
        print("Posted to API endpoint, response: {0}".format(response))
        sys.exit(0)
    except Exception as e:
        print("Unable to post to API endpoint: {0}".format(str(e)))
        sys.exit(1)
