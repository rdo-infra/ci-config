#!/bin/bash
#
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# Mini cleanup script to remove stacks in any failed state.

# Check that we can talk with the cloud
if ! openstack token issue >/dev/null; then
    echo "ERROR: Failed to talk with cloud, credentials should be sourced or configured in cloud.yaml file." >&2
    exit 1;
fi

STACK_NAMES=$(openstack stack list -f json | jq -r '.[] | select(.["Stack Status"] |test("FAILED")) | .["Stack Name"]')
STACK_IDS=$(openstack stack list -f json | jq -r '.[] | select(.["Stack Status"] |test("FAILED")) | .["ID"]')
if [[  -z $STACK_NAMES ]]; then
    echo "INFO: There are no stacks in error to delete" >&2
else
    echo "INFO: There are stacks in FAILED state - $STACK_NAMES" >&2
        for STACK in $STACK_IDS; do
            echo "INFO: Deleting stack ID $STACK ..." >&2
            openstack stack delete -y $STACK
            sleep 10
        done
fi
