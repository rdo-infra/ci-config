#!/usr/bin/env python
import argparse
import os
import subprocess
import time
import re
import json
import datetime

# This file is running on te-broker periodically

FILE_PATH = 'influxdb_stats_vexx'
SECRETS = "/etc/vexxhostrc"
re_ex = re.compile(r"^export ([^\s=]+)=(\S+)")


def _run_cmd(cmd):
    env = os.environ.copy()
    with open(SECRETS) as f:
        d = {}
        for line in f:
            if re_ex.match(line):
                key, val = re_ex.search(line).groups()
                d[key] = val.replace('"', '').replace("'", "")
    env.update(d)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, env=env)
    outs, errs = p.communicate()
    if errs:
        for i in errs:
            print("ERROR %s" % i)
    try:
        output = json.loads(outs)
    except Exception as e:
        print("ERROR %s" % e)
        return None, errs
    return output, errs


def run_server_check():
    cmd = ("openstack server list --project-domain "
           "4b633c451ac74233be3721a3635275e5 --long -f json")
    out = _run_cmd(cmd)[0]
    if not out:
        return None
    d = {}
    statuses = ['ACTIVE', 'BUILD', 'ERROR', 'DELETED']
    for s in statuses:
        d[s] = len([i for i in out if i['Status'] == s])
    d['undercloud'] = len([
        i for i in out
        if i['Flavor Name'] == 'nodepool'
        and "node" in i['Name']
    ])
    d['multinode'] = 0  # can't figure out for vexx
    d['bmc'] = len([i for i in out if i['Image Name'] == 'bmc-template'])
    d['ovb-node'] = len([i for i in out if i['Image Name'] == 'ipxe-boot'])
    d['total'] = len(out)
    d['other'] = (
        d['total'] - d['ovb-node'] - d['bmc']
        - d['undercloud'] - d['multinode'])
    return d


def run_quote_check():
    cmd = "openstack limits show --absolute --quote all -f json"
    out = _run_cmd(cmd)[0]
    if not out:
        return None
    d = {}
    d['cores'] = next(
        iter([i['Value'] for i in out if 'totalCoresUsed' in i['Name']]), 0)
    d['ram'] = next(
        iter([i['Value'] for i in out if 'totalRAMUsed' in i['Name']]), 0)
    d['instances'] = next(
        iter([i['Value'] for i in out if 'totalInstancesUsed' in i['Name']]),
        0)
    d['gbs'] = next(
        iter([i['Value'] for i in out if 'totalGigabytesUsed' in i['Name']]),
        0)
    return d


def run_fips_count():
    cmd = "openstack floating ip list -f json"
    out = _run_cmd(cmd)[0]
    if not out:
        return 0
    return len(out)


def run_ports_down_count():
    cmd = "openstack port list -f json"
    out = _run_cmd(cmd)[0]
    if not out:
        return 0
    downs = [i for i in out if i['Status'] == "DOWN"]
    return len(downs)


def run_stacks_check():
    cmd = "openstack stack list  -f json"
    out = _run_cmd(cmd)[0]
    if not out:
        return None
    d = {}
    d['stacks_total'] = len(out)
    d['create_complete'] = len(
        [i for i in out if i['Stack Status'] == 'CREATE_COMPLETE'])
    d['create_failed'] = len(
        [i for i in out if i['Stack Status'] == 'CREATE_FAILED'])
    d['create_in_progress'] = len(
        [i for i in out if i['Stack Status'] == 'CREATE_IN_PROGRESS'])
    d['delete_in_progress'] = len(
        [i for i in out if i['Stack Status'] == 'DELETE_IN_PROGRESS'])
    d['delete_failed'] = len(
        [i for i in out if i['Stack Status'] == 'DELETE_FAILED'])
    d['delete_complete'] = len(
        [i for i in out if i['Stack Status'] == 'DELETE_COMPLETE'])
    d['old_stacks'] = len([
        i for i in out
        if int((datetime.datetime.now() - datetime.datetime.strptime(
            i['Creation Time'],
            '%Y-%m-%dT%H:%M:%SZ')).total_seconds() / 3600) > 5
    ])
    return d


def compose_influxdb_data(servers, quotes, stacks, fips, ports_down, ts):
    s = ''
    influxdb_data = ''
    if servers:
        s = 'vexxhost-servers '
        s += ('ACTIVE={ACTIVE},BUILD={BUILD},ERROR={ERROR},DELETED={DELETED},'
              ).format(**servers)
        s += ('undercloud={undercloud},multinode={multinode},bmc={bmc},'
              'ovb-node={ovb-node},other={other},total={total}'
              ).format(**servers)
    if stacks:
        if s:
            s += ','
        else:
            s = 'vexxhost-servers '
        s += (
            'stacks_total={stacks_total},create_complete={create_complete},'
            'create_failed={create_failed},'
            'create_in_progress={create_in_progress}'
            ',delete_in_progress={delete_in_progress},'
            'delete_failed={delete_failed},delete_complete={delete_complete},'
            'old_stacks={old_stacks}').format(**stacks)

    p = ''
    if quotes:
        quotes.update({'fips': fips})
        quotes.update({'ports_down': ports_down})
        p = 'vexxhost-perf '
        p += ('instances={instances},cores={cores},ram={ram},gigabytes={gbs},'
              'fips={fips},ports_down={ports_down}'
              ).format(**quotes)
    nanots = str(int(ts)) + "000000000"
    if s:
        influxdb_data = s + " %s\n" % nanots
    if p:
        influxdb_data += p + " %s\n" % nanots

    return influxdb_data


def write_influxdb_file(webdir, influxdb_data):
    with open(os.path.join(webdir, FILE_PATH), "w") as f:
        f.write(influxdb_data)


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve cloud statistics")

    parser.add_argument(
        '--webdir', default="/var/www/html/", help="(default: %(default)s)")
    args = parser.parse_args()

    servers = run_server_check()
    quotes = run_quote_check()
    stacks = run_stacks_check()
    fips = run_fips_count()
    ports_down = run_ports_down_count()
    influxdb_data = compose_influxdb_data(
                        servers, quotes, stacks, fips, ports_down, time.time())
    write_influxdb_file(args.webdir, influxdb_data)


if __name__ == '__main__':
    main()
