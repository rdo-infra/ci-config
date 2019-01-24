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

# This script deletes all heat stacks and associated resources:
# instances, networks, and ports, in a tenant.
# Use the nuclear option with caution. All non-marked ports will be deleted.

: ${LONG_RUNNING:1}
: ${TIME_EXPIRED:=300}
: ${STACK_LIST:=""}
: ${NUCLEAR:=0}
: ${DRY_RUN:=0}
: ${PREFIX:="baremetal_"}
: ${SUFFIX:=""}
: ${SLEEP_TIME:=2}

usage () {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -l, --long-running"
    echo "                      Default option - delete all stacks running longer than"
    echo "                      the time expired."
    echo "  -t, --time-expired"
    echo "                      Time, in minutes, a stack has been running when it will"
    echo "                      be deleted. It is used with the long-running option."
    echo "                      Defaults to 300 minutes (5 hours)"
    echo "  -s, --stack-list"
    echo "                      A list of stacks, and associated resources to delete."
    echo "                      Alternative to the long-running option."
    echo "                      ** The stack list must be passed in quotes **"
    echo "  -n, --nuclear"
    echo "                      Delete all stacks, associated resources,and unmarked ports."
    echo "                      Default is delete only specified stacks and resources."
    echo "                      Use with caution - unmarked ports associated with other instances"
    echo "                      will also be deleted"
    echo "  -d, --dry-run"
    echo "                      Do not delete any stacks or resources. Print out the resources"
    echo "                      that would be deleted."
    echo "                      This option is off by default"
    echo "  -p, --prefix"
    echo "                      Stack name prefix added before the stack unique identifer."
    echo "                      Default is baremetal_"
    echo "  -f, --suffix"
    echo "                      Stack name suffix added after the stack unique identifer."
    echo "                      Default is an empty string"
    echo "  -h, --help          Print this help and exit"
}

set -e

# Check that we can talk with the cloud
if ! openstack token issue 2>&1 >/dev/null; then
    # we attempt to load credentials and avoid xtrace during sourcing
    old_trace_value=$( [[ $- = *x* ]] && echo '-x' || echo '+x')
    set +x
    source /etc/nodepoolrc
    set ${old_trace_value}

    if ! openstack token issue >/dev/null; then
        echo "ERROR: Failed to talk with cloud, credentials should be sourced, configured in cloud.yaml file or stored inside /etc/nodepoolrc file." >&2
        exit 1;
    fi
fi

# Input argument assignments
while [ "x$1" != "x" ]; do

    case "$1" in
        --long-running|-l)
            LONG_RUNNING=1
            ;;

        --time-expired|-t)
            TIME_EXPIRED=$2
            shift
            ;;

        --stack-list|-s)
            STACK_LIST=$2
            shift
            ;;

        --nuclear|-n)
            NUCLEAR=1
            ;;

        --dry-run|-d)
            DRY_RUN=1
            ;;

        --prefix|-p)
            PREFIX=$2
            shift
            ;;

        --suffix|-f)
            SUFFIX=$2
            shift
            ;;

        --help|-h)
            usage
            exit
            ;;

        --) shift
            break
            ;;

        -*) echo "ERROR: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;

        *)    break
            ;;
    esac

    shift
done

# Check input values

if [[ ! "$TIME_EXPIRED" =~ ^[0-9]+$ ]]; then
        echo "ERROR: A time (in minutes) must be defined if -t is passed." >&2
        exit 1
fi
if [[ "$PREFIX" =~ ^[\-].*$ || "$SUFFIX" =~ ^[\-].*$ ]]; then
    echo "ERROR: A prefix and suffix, if defined, must not start with a -." >&2
    exit 1
fi

# Install jq if not already there
# Required to use JSON parsing of openstack client return values

which jq >/dev/null || sudo yum install -y jq

# runs command if not in dry mode
function run {
    if [[ "$DRY_RUN" == "0" ]]; then
        $*
    else
        echo "INFO: DRY: $*"
    fi
}

# Get list of stacks and make a first attempt to delete
# each stack

if [[ ! -z "$STACK_LIST" ]]; then
    echo "INFO: Using the specified stack list to remove stacks." >&2
    LONG_RUNNING=0
elif [[ "$NUCLEAR" == "1" ]]; then
    echo "INFO: Collecting a list of all available Heat stacks ..." >&2
    STACK_LIST=$(openstack stack list -f json | jq -r '.[]| .["ID"]')
else
    echo "INFO: Getting a list of all stacks running longer than $TIME_EXPIRED minutes ..." >&2
    DATE_TIME_EXPIRED=$(`which gdate date 2>/dev/null | head -n1` -d " $TIME_EXPIRED minutes ago" -u  "+%Y-%m-%dT%H:%M:%SZ")
    STACK_LIST=$(openstack stack list -f json | jq --arg date_time_expired "$DATE_TIME_EXPIRED" -r '.[]| select(.["Creation Time"] <= $date_time_expired)  | .["ID"]')
fi

for STACK in $STACK_LIST; do
    echo "INFO: Deleting stack id $STACK ..." >&2
    run openstack stack delete -y $STACK || echo "WARN: stack $STACK failed to clean up" >&2
    # don't overwhelm the tenant with mass delete
    run sleep $SLEEP_TIME
done

#  Check if there are stacks left in CREATE_FAILED or DELETE_FAILED state

STACK_LIST_STATUS=$(openstack stack list -f json | jq -r '.[] | select(.["Stack Status"] |test("(CREATE|DELETE)_FAILED")) | .["Stack Name"]')
if [[  -z $STACK_LIST_STATUS ]]; then
    echo "INFO: There are no stacks to delete, exiting script." >&2
    exit 0
else
    echo "INFO: There are stacks in *_FAILED state - $(echo $STACK_LIST_STATUS | paste -sd "," -)" >&2
    echo "INFO: Remove associated resources and then delete the stacks again." >&2

    # NUCLEAR OPTION - Remove all non-marked ports

    if [[ "$NUCLEAR" == "1" ]]; then
        PORT_LIST_EMPTY_ID=$(openstack port list -f json | jq -r '.[] | select(.["Name"] == "") | .["ID"]')
        for PORT in $PORT_LIST_EMPTY_ID; do
            echo "INFO: Deleting port with empty name, ID $PORT ..." >&2
            run openstack port delete $PORT
        done
    fi

    # Delete ports, instances, and networks from stacks
    # in 'delete_failed' state

    for STACK in $STACK_LIST_STATUS; do

        # Extract identifier for associated resources
        IDENTIFIER=${STACK#$PREFIX}
        IDENTIFIER=${IDENTIFIER%$SUFFIX}
        echo "INFO: Stack identifier is $IDENTIFIER" >&2

        # Delete associated instances/servers
        SERVER_IDS=$(openstack server list -f value -c ID --name \"-${IDENTIFIER}_\" -c ID)
        for SERVER in $SERVER_IDS; do
            echo "INFO: Deleting server ID $SERVER ..." >&2
            run openstack server delete $SERVER
        done

        # Delete ports with identifier in the name
        PORT_IDS=$(openstack port list -f json |  jq -r --arg IDENTIFIER "-${IDENTIFIER}_" '.[] | select(.["Name"] | contains($IDENTIFIER))| .["ID"]')
        for PORT in $PORT_IDS; do
            echo "INFO: Deleting port ID $PORT ..." >&2
            run openstack port delete $PORT
        done

        # Networks - delete empty ports associated with subnets and then networks
        SUBNET_IDS=$(openstack subnet list -f json |  jq -r --arg IDENTIFIER "-${IDENTIFIER}" '.[] | select(.["Name"] | endswith($IDENTIFIER)) | .["ID"]')
        for SUBNET_ID in $SUBNET_IDS; do
            PORT_SUBNET_IDS=$(openstack port list -f json |  jq -r --arg SUBNET_ID "$SUBNET_ID" '.[] | select(.["Fixed IP Addresses"] | contains($SUBNET_ID)) | .["ID"]')
            for PORT_SUBNET_ID in $PORT_SUBNET_IDS; do
                echo "INFO: Deleting port ID $PORT_SUBNET_ID ..." >&2
                run openstack port delete $PORT_SUBNET_ID
            done
        done

        NETWORK_IDS=$(openstack network list -f json |  jq -r --arg IDENTIFIER "-${IDENTIFIER}" '.[] | select(.["Name"] | endswith($IDENTIFIER)) | .["ID"]')
        for NETWORK_ID in $NETWORK_IDS; do
            echo "INFO: Deleting network ID $NETWORK_ID ..." >&2
            run openstack network delete $NETWORK_ID
        done

        # Delete the stack again, will log stack_status_reason
        for (( DELETE_TIMES=0; DELETE_TIMES <= 4; DELETE_TIMES++ )); do
            echo "INFO: Retry loop attempt $DELETE_TIMES..."
            STACK_LIST_STATUS=$(openstack stack list -f json | jq -r '.[] | select(.["Stack Status"] |test("(CREATE|DELETE)_FAILED")) | .["Stack Name"]')
            if [[  -z $STACK_LIST_STATUS ]]; then
                break
            fi
            for STACK in $STACK_LIST_STATUS; do
                echo "INFO: Deleting stack id $STACK..." >&2
                run openstack stack delete -y $STACK
                # don't overwhelm the tenant with mass delete
                run sleep $SLEEP_TIME
            done
        done

    done

fi
