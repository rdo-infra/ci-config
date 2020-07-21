#!/usr/bin/env python
import argparse
from datetime import datetime
import json
from diskcache import Cache
import requests


CACHE_SIZE = int(1e9)  # 1GB

cache = Cache('/tmp/gerrt_changes_cache', size_limit=CACHE_SIZE)
cache.expire()


def time_convert(t, nano=True):
    return datetime.strptime(t[:-10], '%Y-%m-%d %H:%M:%S').strftime('%s') + (
        '000000000' if nano else '')


def influx_esc(s):
    s = s.replace('"', '\\"')
    s = s.replace(',', '\\,')
    s = s.replace("'", '\\"')
    s = s.replace(" ", '\\ ')
    return s


def get_username(host, uid):
    if uid in cache:
        return cache[uid]
    user = requests.get("%s/accounts/%s" % (host, uid))
    if user.ok:
        json_raw = user.content[5:]
        try:
            json_data = json.loads(json_raw)
        except Exception:
            return ''
        username = json_data.get('name')
        cache.add(uid, username, expire=None)
        return username
    return ''


def get_gerrit_data(host, project):
    url = (
        "%s/changes/?q=status:open+project:%s"
        "+-label:Workflow=-1+-label:Code-Review=-2"
        "+-message:\"WIP\"+-message:\"DNM\"") % (
        host, project)
    data = requests.get(url)
    json_raw = data.content[5:]
    try:
        json_data = json.loads(json_raw)
        return json_data
    except Exception:
        return None


def pretty_print(patch, host, project):
    patch_id = patch['_number']
    patch_created = time_convert(patch['created'], nano=False) + "000"
    patch_updated = time_convert(patch['updated'], nano=False) + "000"
    patch_mergeable = patch['mergeable']
    patch_title = patch['subject']
    patch_user = get_username(host, patch['owner']['_account_id'])
    patch_link = "<a href='%s/%s' target=_blank>%s</a>" % (
        host, patch_id, patch_title)
    return ('patch,'
            'id=%s,'
            'created=%s,'
            'updated=%s,'
            'mergeable=%s,'
            'owner=%s,'
            'project=%s'
            ' '
            'id=%s,'
            'created=%s,'
            'updated=%s,'
            'mergeable=%s,'
            'owner="%s",'
            'subject="%s",'
            'project="%s",'
            'link="%s"'
            ' '
            '%s' % (
                patch_id,
                patch_created,
                patch_updated,
                patch_mergeable,
                influx_esc(patch_user),
                project,

                patch_id,
                patch_created,
                patch_updated,
                patch_mergeable,
                patch_user,
                patch_title,
                project,
                patch_link,
                time_convert(
                    patch['created'], nano=True)
            ))


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve Gerrit statistics")

    parser.add_argument(
        '--host', default="https://review.opendev.org",
        help="(default: %(default)s)")
    parser.add_argument('--project', help='Project name in Gerrit'
                        '(including "openstack/")')
    args = parser.parse_args()

    changes = get_gerrit_data(args.host, args.project)
    if changes:
        patches = [pretty_print(c, args.host, args.project) for c in changes]
        for p in patches:
            print(p)


if __name__ == '__main__':
    main()
