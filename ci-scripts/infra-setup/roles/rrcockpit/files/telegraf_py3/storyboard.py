#!/usr/bin/env python
import argparse
from datetime import datetime

import requests
from diskcache import Cache

CACHE_SIZE = int(1e9)  # 1GB

cache = Cache('/tmp/storyboard_cache', size_limit=CACHE_SIZE)
cache.expire()


def get_storyboard_data(host, project, status, limit):
    url = ("%s/api/v1/stories?"
           "limit=%s&project_id=%s&sort_dir=desc&status=%s") % (
        host, limit, project, status)
    data = requests.get(url)
    if data.ok:
        return data.json()


def get_username(host, uid):
    if uid in cache:
        return cache[uid]
    user = requests.get("%s/api/v1/users/%s" % (host, uid))
    if user.ok:
        data = user.json()
        username = data.get('full_name')
        cache.add(uid, username, expire=None)
        return username
    return 'N/A'


def time_convert(t, nano=True):
    return datetime.strptime(t[:-6], '%Y-%m-%dT%H:%M:%S').strftime('%s') + (
        '000000000' if nano else '')


def influx_esc(s):
    s = s.replace('"', '\\"')
    s = s.replace(',', '\\,')
    s = s.replace("'", '\\"')
    s = s.replace(" ", '\\ ')
    return s


def extract_story(story, host):
    sid = story['id']
    s_created = time_convert(story['created_at'], nano=False)
    s_updated = time_convert(story['updated_at'], nano=False)
    s_user = get_username(host, story['creator_id'])
    s_title = story['title'].replace('"', "'").replace(',', ' ')
    s_current = "-".join(
        [i['key'] for i in story['task_statuses'] if i['count']])
    s_not_started = s_current == 'todo'
    s_link = "<a href='%s/#!/story/%s' target=_blank>%s</a>" % (
        host, sid, s_title)
    return ('story,'
            'id=%s,'
            'created=%s,'
            'updated=%s,'
            'user=%s,'
            'current=%s'
            ' '
            'id=%s,'
            'created=%s,'
            'updated=%s,'
            'user="%s",'
            'title="%s",'
            'current="%s",'
            'not_started=%s,'
            'link="%s"'
            ' '
            '%s' % (
                sid,
                s_created,
                s_updated,
                influx_esc(s_user),
                s_current,
                sid,
                s_created + "000",
                s_updated + "000",
                s_user,
                s_title,
                s_current,
                s_not_started,
                s_link,
                time_convert(story['created_at'], nano=True)
            ))


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve storyboard statistics")

    parser.add_argument(
        '--host', default="https://storyboard.openstack.org",
        help="(default: %(default)s)")
    parser.add_argument('--project-id', help='Project ID in storyboard')
    parser.add_argument('--story-status', default='active',
                        help='Status of stories to get (default: %(default)s)')
    parser.add_argument('--limit', default=10,
                        help='Limit stories to specific number')
    args = parser.parse_args()

    stories_json = get_storyboard_data(args.host, args.project_id,
                                       args.story_status, args.limit)
    if stories_json:
        stories = [extract_story(story, args.host) for story in stories_json]
        for s in stories:
            print(s)


if __name__ == '__main__':
    main()
