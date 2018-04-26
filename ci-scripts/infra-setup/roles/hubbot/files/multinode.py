import argparse
import logging
import logging.handlers
import os
import shelve
import sys
import time
import requests
from requests.auth import HTTPBasicAuth


DB_PATH = os.path.join(os.environ['HOME'], "multinode_db")
ZUUL_API_URL = "http://zuul.openstack.org/api/"
ZUUL_API_URL_BUILDS = ZUUL_API_URL + "builds?"
LOG_FILE = "/tmp/multinode.log"
JOBS = [
    "tripleo-ci-centos-7-3nodes-multinode",
    "tripleo-ci-centos-7-containers-multinode",
    "tripleo-ci-centos-7-nonha-multinode-oooq",
    "tripleo-ci-centos-7-scenario000-multinode-oooq-container-updates",
    "tripleo-ci-centos-7-scenario001-multinode-oooq",
    "tripleo-ci-centos-7-scenario001-multinode-oooq-container",
    "tripleo-ci-centos-7-scenario002-multinode-oooq",
    "tripleo-ci-centos-7-scenario002-multinode-oooq-container",
    "tripleo-ci-centos-7-scenario003-multinode-oooq",
    "tripleo-ci-centos-7-scenario003-multinode-oooq-container",
    "tripleo-ci-centos-7-scenario004-multinode-oooq",
    "tripleo-ci-centos-7-scenario004-multinode-oooq-container",
    "tripleo-ci-centos-7-scenario005-multinode-oooq",
    "tripleo-ci-centos-7-scenario006-multinode-oooq",
    "tripleo-ci-centos-7-scenario007-multinode-oooq",
    "tripleo-ci-centos-7-scenario007-multinode-oooq-container",
    "tripleo-ci-centos-7-scenario008-multinode-oooq",
    "tripleo-ci-centos-7-scenario009-multinode-oooq",
    "tripleo-ci-centos-7-scenario010-multinode-oooq-container",
    "tripleo-ci-centos-7-undercloud-containers",
    "tripleo-ci-centos-7-undercloud-oooq",
    "tripleo-ci-centos-7-undercloud-upgrades",
]

log = logging.getLogger('multinodeparser')
log.setLevel(logging.DEBUG)
log_handler = logging.handlers.WatchedFileHandler(
    os.path.expanduser(LOG_FILE), mode='w')
log_formatter = logging.Formatter('%(asctime)s %(process)d '
                                  '%(levelname)-8s %(name)s %(message)s')
log_handler.setFormatter(log_formatter)
log.addHandler(log_handler)


class Web:
    def __init__(self, url):
        self.url = url

    def get_json(self):
        result = requests.get(self.url)
        log.debug('Request for URL=%s got status %s',
                  self.url, result.status_code)
        if result.ok:
            try:
                json_result = result.json()
                log.debug(
                    'Successfully extracted JSON with length=%d from URL=%s',
                    len(json_result), self.url)
            except Exception as e:  # pylint: disable=W0703
                log.error("Can't parse JSON from URL: %s, error=%s",
                          self.url, e)
                return
        else:
            log.error("Got status %s form URL: %s", result.status_code,
                      self.url)
            return
        return json_result

    def get(self):
        result = requests.get(self.url)
        log.debug('Request for URL=%s got status %s', self.url,
                  result.status_code)
        if result.ok:
            return result.content
        log.error(
            "Got status %s form URL: %s", result.status_code, self.url)
        return


class InfluxDB:
    def __init__(self, credentials):
        self.auth = None
        self.url = credentials['url'] + "write?"
        user = credentials.get('user')
        passw = credentials.get('passw')
        db = credentials['db']
        if user and passw:
            self.auth = HTTPBasicAuth(user, passw)
        self.params = {"db": db, "precision": "s"}

    def send(self, payload):
        log.debug("Sending request to DB: %s", self.url)
        req = requests.post(self.url, params=self.params, data=payload,
                            auth=self.auth, verify=False)
        if not req.ok:
            log.debug(req.status_code)
            log.debug(req.request.headers)
            log.error(
                "Failed to send write request to InfluxDB. HTTP code=%s",
                req.status_code)


def get_builds(job_name, pages=2):
    result = []
    for i in range(pages):
        skip = '' if i == 0 else '&skip=%s' % (50 * i)
        web = Web(ZUUL_API_URL_BUILDS + 'job_name=%s' % job_name + skip)
        ret = web.get_json()
        if not ret:
            log.error("Failed to get builds for job %s", job_name)
            ret = []
        result += ret
    return result


def check_if_processed(build):
    d = shelve.open(DB_PATH)
    check = str(build['log_url']) in d
    d.close()
    return check


def process(build, credentials, only_passed=True):
    if only_passed and build['result'] != 'SUCCESS':
        return
    influx = InfluxDB(credentials)
    log_url = build['log_url']
    file_url = log_url + "logs/influxdb_data"
    file_content = Web(file_url).get()
    if file_content:
        influx.send(file_content)
    d = shelve.open(DB_PATH)
    d[str(build['log_url'])] = True
    d.close()


def parse(file_path):
    if not os.path.exists(file_path):
        log.error("File doesn't exist %s", file_path)
        sys.exit(1)
    with open(file_path) as f:
        creds = {}
        for line in f:
            if "=" in line:
                key, value = [i.strip() for i in line.split("=")]
                creds[key] = value
    return creds


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('-c', '--creds', dest="credsfile", required=True,
                        help='Path to credentials file for InfluxDB')
    args = parser.parse_args()
    credentials = parse(args.credsfile)
    for job in JOBS:
        builds = get_builds(job)
        for build in builds:
            is_processed = check_if_processed(build)
            if not is_processed:
                process(build, credentials)
                time.sleep(.5)


if __name__ == '__main__':
    main()
