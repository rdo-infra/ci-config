#!/usr/bin/env python
import argparse
import logging
import logging.handlers
import os
import shelve
import sys
import time
import requests
from requests.auth import HTTPBasicAuth


DB_PATH = os.path.join(os.environ['HOME'], "ovb_db")
ZUUL_API_URL = "https://review.rdoproject.org/zuul/api/"
ZUUL_API_URL_BUILDS = ZUUL_API_URL + "builds?"
LOG_FILE = "/tmp/ovb.log"
JOBS = [
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset010-master",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset010-pike",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset010-queens",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset010-rocky",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset016-master",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset016-pike",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset016-queens",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset016-rocky",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset017-master",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset017-pike",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset017-queens",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset017-rocky",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset018-master",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset018-pike",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset018-queens",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset018-rocky",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset019-master",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset019-pike",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset019-queens",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset019-rocky",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset030-master",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset030-queens",
    "legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset030-rocky",
    ("legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset037-"
     "updates-master"),
    ("legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset037-"
     "updates-queens"),
    ("legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset037-"
     "updates-rocky"),
    ("legacy-periodic-tripleo-ci-centos-7-multinode-1ctlr-featureset050-"
     "upgrades-master"),
    ("legacy-periodic-tripleo-ci-centos-7-ovb-1ctlr_1comp_1ceph-featureset024-"
     "pike"),
    ("legacy-periodic-tripleo-ci-centos-7-ovb-1ctlr_1comp-featureset002-master"
     "-upload"),
    ("legacy-periodic-tripleo-ci-centos-7-ovb-1ctlr_1comp-featureset002-ocata-"
     "upload"),
    ("legacy-periodic-tripleo-ci-centos-7-ovb-1ctlr_1comp-featureset002-pike-"
     "upload"),
    ("legacy-periodic-tripleo-ci-centos-7-ovb-1ctlr_1comp-featureset002-"
     "queens-upload"),
    ("legacy-periodic-tripleo-ci-centos-7-ovb-1ctlr_1comp-featureset002-rocky-"
     "upload"),
    "legacy-periodic-tripleo-ci-centos-7-ovb-1ctlr_1comp-featureset020-master",
    "legacy-periodic-tripleo-ci-centos-7-ovb-1ctlr_1comp-featureset020-ocata",
    "legacy-periodic-tripleo-ci-centos-7-ovb-1ctlr_1comp-featureset020-pike",
    "legacy-periodic-tripleo-ci-centos-7-ovb-1ctlr_1comp-featureset020-queens",
    "legacy-periodic-tripleo-ci-centos-7-ovb-1ctlr_1comp-featureset020-rocky",
    "legacy-periodic-tripleo-ci-centos-7-ovb-1ctlr_1comp-featureset021-master",
    "legacy-periodic-tripleo-ci-centos-7-ovb-1ctlr_1comp-featureset021-ocata",
    "legacy-periodic-tripleo-ci-centos-7-ovb-1ctlr_1comp-featureset021-pike",
    "legacy-periodic-tripleo-ci-centos-7-ovb-1ctlr_1comp-featureset021-queens",
    "legacy-periodic-tripleo-ci-centos-7-ovb-1ctlr_1comp-featureset021-rocky",
    "legacy-periodic-tripleo-ci-centos-7-ovb-1ctlr_1comp-featureset022-pike",
    "legacy-periodic-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset001-master",
    "legacy-periodic-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset001-ocata",
    "legacy-periodic-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset001-pike",
    "legacy-periodic-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset001-queens",
    "legacy-periodic-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset001-rocky",
    "legacy-periodic-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset035-master",
    "legacy-periodic-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset035-queens",
    "legacy-periodic-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset035-rocky",
    "legacy-periodic-tripleo-ci-centos-7-singlenode-featureset027-master",
    "legacy-periodic-tripleo-ci-centos-7-singlenode-featureset027-rocky",
    ("legacy-periodic-tripleo-ci-centos-7-singlenode-featureset050-upgrades"
     "-rocky"),
    "legacy-tripleo-ci-centos-7-containers-multinode-upgrades-pike",
    "legacy-tripleo-ci-centos-7-containers-multinode-upgrades-pike-branch",
    ("legacy-tripleo-ci-centos-7-container-to-container-featureset051-"
     "upgrades-master"),
    "legacy-tripleo-ci-centos-7-container-to-container-upgrades-master",
    "legacy-tripleo-ci-centos-7-container-to-container-upgrades-queens",
    "legacy-tripleo-ci-centos-7-multinode-1ctlr-featureset016-master",
    "legacy-tripleo-ci-centos-7-multinode-1ctlr-featureset017-master",
    "legacy-tripleo-ci-centos-7-multinode-1ctlr-featureset018-master",
    "legacy-tripleo-ci-centos-7-multinode-1ctlr-featureset019-master",
    "legacy-tripleo-ci-centos-7-multinode-1ctlr-featureset036-oc-ffu-queens",
    "legacy-tripleo-ci-centos-7-multinode-1ctlr-featureset037-updates-master",
    "legacy-tripleo-ci-centos-7-ovb-1ctlr_1comp_1ceph-featureset024-ocata",
    "legacy-tripleo-ci-centos-7-ovb-1ctlr_1comp_1ceph-featureset024-pike",
    "legacy-tripleo-ci-centos-7-ovb-1ctlr_1comp-featureset020-master",
    "legacy-tripleo-ci-centos-7-ovb-1ctlr_1comp-featureset022-pike",
    "legacy-tripleo-ci-centos-7-ovb-3ctlr_1comp_1supp-featureset039-master",
    "legacy-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset001-master",
    "legacy-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset001-ocata",
    "legacy-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset001-ocata-branch",
    "legacy-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset001-pike",
    "legacy-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset001-pike-branch",
    "legacy-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset001-queens",
    "legacy-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset001-queens-branch",
    "legacy-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset021-master",
    "legacy-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset021-ocata",
    "legacy-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset021-pike",
    "legacy-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset021-queens",
    "legacy-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset035-master",
    "legacy-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset035-queens",
    "legacy-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset042-master",
    "legacy-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset042-master-tht",
    "legacy-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset042-queens",
    "legacy-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset042-queens-tht",
    "legacy-tripleo-ci-centos-7-ovb-3ctlr_1comp-featureset053-master",
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
        log.debug("Sending request to DB: %s: %s", self.url, payload)
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
