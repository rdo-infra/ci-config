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
}

load_db(){
   read_lp > /tmp/lp.csv
   mysql -h mariadb -P 3306 -u root < /tmp/load_lp_mysql.sql
}

# We could have just keep sleep 60 before load_db, but this helps dev
# itearations, you don't have to wait 1 minute everytime you change stuff
# at mariadb-sidecar
ansible-playbook /tmp/wait-mariadb.yaml

while true; do
  load_db 2>&1 | tee /tmp/run.log
  sleep 60;
done
