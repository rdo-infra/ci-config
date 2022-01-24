import os
import re

from perfcomp.utils import get_file, red, green
from perfcomp.filediff import make_diff
from perfcomp.config import RPM_LOC, NAME_TO_PROJECT


PKG_NAME = re.compile(r'(^[a-z0-9-]+)-[0-9]+\.')
COMMIT_HASH = re.compile(r'\.20\d+\.([a-z0-9]{7})\.')


def name_extract(name):
    re_name = PKG_NAME.search(name)
    return re_name.group(1) if re_name else ''


def check_packages(inline, uniq1, uniq2):
    # extract names in uniqs
    uniq1_names = {name_extract(u): u for u in uniq1}
    uniq2_names = {name_extract(u): u for u in uniq2}
    # find common
    common = [i for i in list(set(uniq1_names).intersection(uniq2_names)) if i]
    if common:
        for u in common:
            inline.append((uniq1_names[u], uniq2_names[u]))
            uniq1.remove(uniq1_names[u])
            uniq2.remove(uniq2_names[u])
    return inline, uniq1, uniq2


def rpms(good, bad):
    g = get_file(good, RPM_LOC, json_file=False)
    b = get_file(bad, RPM_LOC, json_file=False)
    if g is None or b is None:
        raise Exception("No RPMs files are found")
    files_diff = make_diff(fromstr=g, tostr=b)
    return files_diff


def colorize_diff(pair):
    common_part = os.path.commonprefix(pair)
    diff_parts = [i.replace(common_part, '') for i in pair]
    return [
        pair[0].replace(diff_parts[0], green(diff_parts[0])),
        pair[1].replace(diff_parts[1], red(diff_parts[1]))]


def extract_commit_hash(x):
    commit_hash = COMMIT_HASH.search(x)
    return commit_hash.group(1) if commit_hash else ''


def add_github_links(inline, colored):
    def add_github(p):
        hash1 = extract_commit_hash(p[0])
        hash2 = extract_commit_hash(p[1])
        if not hash1 or not hash2:
            return ''
        link = "https://github.com/%s/compare/%s..%s"
        pkg_name = PKG_NAME.search(p[0])
        if not pkg_name:
            return ''
        pkg_name = pkg_name.group(1)
        project = NAME_TO_PROJECT.get(pkg_name, '')
        if not project:
            return ''
        # The diff is from hash2 -> to hash1
        link = link % (project, hash2, hash1)
        return link

    for index, pair in enumerate(inline):
        diff_link = add_github(pair)
        colored[index].append(diff_link)
    return colored
