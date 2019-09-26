#!/usr/bin/env python
import argparse
import datetime
import re

from perfcomp.utils import log, get_file, json_from_sql, save_to_file
from perfcomp.config import DATA, SQLITE_FILES


TASK_NAME = re.compile('^[^:]+ : ')


def name_simplify(name):
    return TASK_NAME.sub('', name)


def normalize(data):

    def time_delta(ts):
        t = datetime.datetime.strptime(ts, "%H:%M:%S")
        return int(datetime.timedelta(hours=t.hour, minutes=t.minute,
                                      seconds=t.second).total_seconds())

    norm = [{'name': name_simplify(i['Name']),
             'time': time_delta(i['Duration'])}
            for i in data]
    dictized = {}
    for i in norm:
        if i['name'] in dictized:
            dictized[i['name']] += i['time']
        else:
            dictized[i['name']] = i['time']
    total_norm = []
    for i in norm:
        if i['name'] in dictized:
            total_norm.append(
                {'name': i['name'], 'time': dictized.pop(i['name'])}
            )
    norm_names = [i['name'] for i in total_norm]
    import time
    with open("/tmp/devb_%s" % time.time(), "w") as f:
        f.write(str(total_norm))
    time.sleep(1)
    return norm_names, total_norm


def combine(data1, data2):
    data = []
    norm1_names, norm1 = normalize(data1)
    norm2_names, norm2 = normalize(data2)
    for task in norm1:
        if task['name'] in norm2_names:
            task2 = [i for i in norm2 if i['name'] == task['name']][0]
            data += [[task['name'], task['time'], task2['time']]]
            norm2.remove(task2)
        else:
            data += [[task['name'], task['time'], 0]]
    for task in norm2:
        data += [[task['name'], 0, task['time']]]
    return data


def filter_data(data):
    f1 = (i for i in data if not (i[1] == 0 and i[2] == 0))
    f2 = (i for i in f1 if abs(i[1] - i[2]) > 10)
    return list(f2)


def extract(link1, link2, filepath):
    data1 = get_file(link1, filepath)
    if data1 == "not found":
        return None
    data2 = get_file(link2, filepath)
    if data2 == "not found":
        return None
    if data1 and data2:
        return data1, data2
    return None


def sqlite_extract(link1, link2, filepath):
    data1 = get_file(link1, filepath, json_file=False)
    if data1 == "not found":
        return None
    data2 = get_file(link2, filepath, json_file=False)
    if data1 == "not found":
        return None
    if data1 and data2:
        data_1, data_2 = json_from_sql(data1), json_from_sql(data2)
        if data_1 and data_2:
            return data_1, data_2
    return None


def compare(good, bad):
    ready = {}
    for part, filepath in DATA.items():
        log.debug("Checking file %s", filepath)
        extracted_data = extract(good, bad, filepath)
        if extracted_data is None:
            extracted_data = sqlite_extract(good, bad, SQLITE_FILES[part])
            if extracted_data is None:
                ready[part] = None
                continue
        combined_data = combine(*extracted_data)
        filtered_data = filter_data(combined_data)
        ready[part] = filtered_data
    return ready


def main():
    parser = argparse.ArgumentParser(__doc__)

    parser.add_argument('-g', '--good-job', dest="good",
                        default=("https://logs.rdoproject.org/96/15896/35/"
                                 "check/legacy-tripleo-ci-centos-7-ovb-3ctlr_"
                                 "1comp-featureset001-master/3cf4a97/"),
                        help='Link to good job')
    parser.add_argument('-b', '--bad-job', dest="bad",
                        default=("https://logs.rdoproject.org/96/15896/35/"
                                 "check/legacy-tripleo-ci-centos-7-ovb-3ctlr_"
                                 "1comp-featureset001-master-vexxhost/"
                                 "2b2cbf3/"),
                        help='Link to bad job')
    args = parser.parse_args()
    data = compare(args.good, args.bad)
    save_to_file(data)
    print(data)


if __name__ == '__main__':
    main()
