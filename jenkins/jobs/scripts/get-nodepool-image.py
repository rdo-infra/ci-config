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

# Returns the latest nodepool image matching a pattern from a cloud

import argparse
import shade
import sys


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('cloud', help='name of the cloud in clouds.yaml')
    parser.add_argument('--pattern', help='image name pattern to look for',
                        default='template-rdo-centos-7')
    args = parser.parse_args()
    return args


def main():
    args = get_args()
    cloud = shade.openstack_cloud(cloud=args.cloud)

    # List all images
    images = cloud.list_images()

    # From those images, only pick the ones that have been uploaded by nodepool
    # and match our pattern
    nodepool_images = [
        image
        for image in images
        if 'nodepool_build_id' in image['properties'] and  # noqa: W504
        args.pattern in image['name']
    ]
    if nodepool_images:
        # If there are any matches, alphabetically sort them by name
        # This allows us to easily get the latest image since nodepool suffixes
        # a unix timestamp at the end after the pattern.
        nodepool_images = sorted(nodepool_images, key=lambda k: k['name'])
        print(nodepool_images[-1]['name'])
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
