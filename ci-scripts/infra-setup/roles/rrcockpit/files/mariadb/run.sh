#!/bin/bash
set -x

read_lp(){
    launchpad_bugs_mariadb.py \
        --tag alert \
        --status \
            New \
            Confirmed \
            Triaged \
            'In Progress' \
            'Fix Committed' \
            Incomplete

    launchpad_bugs_mariadb.py \
        --tag promotion-blocker \
        --status \
            New \
            Confirmed \
            Triaged \
            'In Progress' \
            'Fix Committed' \
            Incomplete

    launchpad_bugs_mariadb.py \
        --tag tempest \
        --status \
            New \
            Confirmed \
            Triaged \
            'In Progress' \
            'Fix Committed' \
            Incomplete
}

read_noop(){
    releases="master rocky queens pike"
    types="upstream rdo tempest"
    for release in $releases; do
        for type in $types; do
            noop_build.py --release $release --type $type
        done
    done
}

load_mariadb(){
    read_$1 > /tmp/$1.csv
    mysql -h mariadb -P 3306 -u root < /tmp/load_$1_mysql.sql
}

# We could have just keep sleep 60 before load_db, but this helps dev
# itearations, you don't have to wait 1 minute everytime you change stuff
# at mariadb-sidecar
ansible-playbook /tmp/wait-mariadb.yaml

while true; do
    load_mariadb noop 2>&1 | tee /tmp/run.log
    load_mariadb lp 2>&1 | tee /tmp/run.log
    sleep 60;
done
