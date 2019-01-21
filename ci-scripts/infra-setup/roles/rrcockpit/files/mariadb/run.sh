#!/bin/bash
set -x

load_db(){
  python /tmp/launchpad_bugs_mariadb.py --tag alert --status New Confirmed Triaged 'In Progress' 'Fix Committed' Incomplete > /tmp/lp.csv

  python /tmp/launchpad_bugs_mariadb.py --tag promotion-blocker --status New Confirmed Triaged 'In Progress' 'Fix Committed' Incomplete >> /tmp/lp.csv

  mysql -h mariadb -P 3306 -u root < /tmp/load_lp_mysql.sql 
}

while true; do
  sleep 60;
  load_db &>> /tmp/run.log || true;
done
