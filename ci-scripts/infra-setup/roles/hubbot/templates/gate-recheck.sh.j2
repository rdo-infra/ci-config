#!/bin/bash

CHANGE_ID="I2e4b8f2db0e245bef73b99e12975ae275104f9c4"

# get the latest commit hash
HASH=$(ssh -p 29418 adarazs@review.openstack.org gerrit query --format json --current-patch-set $CHANGE_ID |jq -r '.["currentPatchSet"]["revision"]'|head -n 1)

if [ $? != 0 ]; then
    echo "Failed to get the latest change"
    exit 1
fi

# rebase
ssh -p 29418 adarazs@review.openstack.org gerrit review --rebase $HASH

# if rebase failed (probably already the latest), then recheck
if [ "$?" != "0" ]; then
    ssh -p 29418 adarazs@review.openstack.org gerrit review --message "recheck" $HASH
fi
