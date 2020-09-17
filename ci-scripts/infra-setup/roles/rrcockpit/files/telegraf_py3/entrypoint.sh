#!/bin/sh
set -e

echo login $TG_GERRIT_SERVICE_USER >> /root/.netrc
echo password $TG_GERRIT_SERVICE_PASSWORD >> /root/.netrc

telegraf --debug --config-directory /etc/telegraf/telegraf.d/ --input-filter exec

exit 0
