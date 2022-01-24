import json
import logging
import logging.handlers
import os
import subprocess
import requests
from six.moves.urllib.parse import urljoin

from perfcomp.config import LOG_FILE, FILE_STORAGE


log = logging.getLogger('comparator')
log.setLevel(logging.DEBUG)
log_handler = logging.handlers.WatchedFileHandler(
    os.path.expanduser(LOG_FILE))
log_formatter = logging.Formatter('%(asctime)s %(process)d '
                                  '%(filename)s:%(lineno)s:%(funcName)s '
                                  '%(levelname)s %(name)s %(message)s')
log_handler.setFormatter(log_formatter)
log.addHandler(log_handler)


def normalize_filename(f):
    return f.replace("/", "_")


def check_json(j, url=""):
    try:
        jsoned = json.loads(j)
        return jsoned
    except Exception as e:
        log.error("Couldn't parse JSON %s\n%s", url, e)
        return None


def cache_file_path(logsdir, file_name, base_path=FILE_STORAGE, subdir=""):
    file_name = normalize_filename(file_name)
    return os.path.join(base_path, subdir, logsdir, file_name)


def check_cache(filedir, file_path):
    file_path = normalize_filename(file_path)
    cache = cache_file_path(filedir, file_path)
    return cache if os.path.exists(cache) else None


def save_cache(filedir, file_path, content):
    file_path = normalize_filename(file_path)
    cache = cache_file_path(filedir, file_path)
    dir_path = os.path.dirname(cache)
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
        except OSError:
            log.error("Creation of the directory %s failed", dir_path)
            return
        else:
            log.info("Successfully created the directory %s", dir_path)
    log.debug("Saving to cache %s", cache)
    with open(cache, "wb") as cf:
        cf.write(content)


def get_file(link, filepath, json_file=True):
    url = urljoin(link, "logs/" + filepath)
    logs_id = link.rstrip("/").split("/")[-1]
    cache_file = check_cache(logs_id, filepath)
    if cache_file:
        log.debug("Using cached file %s", cache_file)
        with open(cache_file, "rb") as cf:
            if json_file:
                return check_json(cf.read(), url)
            return cf.read()
    www = requests.get(url)
    if www is not None and www.status_code == 404:
        log.debug("Web request for %s got 404", url)
        url = url + ".gz"
        www = requests.get(url)
        if www and www.status_code == 404:
            log.debug("Web request for %s got 404", url)
            return None
    if not www or www.status_code not in (200, 404):
        log.debug("Web request for %s failed with status code %s",
                  url, str(www.status_code))
        return None
    content = www.content
    save_cache(logs_id, filepath, content)
    if json_file:
        return check_json(content, url)
    return content


def json_from_sql(sql):
    temp_file = os.path.join(FILE_STORAGE, "ara_tmp.sqlite")
    with open(temp_file, "wb") as f:
        f.write(sql)
    cmd = "ARA_DATABASE='sqlite:///%s' ara task list --all -f json"
    result = subprocess.check_output(
        cmd % temp_file, stderr=subprocess.STDOUT, shell=True)
    try:
        json_data = json.loads(result)
    except Exception:
        log.error("Couldn't parse JSON from saved sqlite: %s...",
                  str(result)[:20])
        return None
    return json_data


def save_to_file(data):
    with open(os.path.join(FILE_STORAGE, "compare_data"), "w") as f:
        for k in data:
            f.write("\n" + k + ":\n\n")
            print(data[k])
            if data[k]:
                for z in data[k]:
                    f.write(" | ".join([str(l) for l in z]) + "\n")


def red(x):
    return '<span style="background-color: #ffaaaa">%s</span>' % x


def green(x):
    return '<span style="background-color: #aaffaa">%s</span>' % x
