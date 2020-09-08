#!/usr/bin/python3

import click
import requests

jenkins_url = "https://ci.centos.org/"
jenkins_query = ("?tree=jobs[name,builds[fullDisplayName,id,url,"
                 + "logs,number,timestamp,duration,result]]"
                 + "&xpath=/hudson/job/build"
                 + "[count(result)=0]&wrapper=builds")


def request_data():

    r = requests.get(jenkins_url + "/api/json" + jenkins_query, verify=False)
    return r


def print_data(data, release):

    jobs = data.json()['jobs']

    for j in jobs:
        if 'builds' in j.keys():
            job_name = j['name']
            # hard code filter on master-promote jobs
            if 'tripleo-quickstart' in job_name:
                if release in job_name:
                    for b in j['builds']:
                        b['timestamp'] = int(b['timestamp'] * 1000000)
                        print(('jenkins,'
                               'job_name={},build_id="{}",'
                               'duration="{}",result="{}",'
                               'url="{}" result="{}",'
                               'url="{}",build_id="{}",'
                               'duration="{}" {}').
                              format(job_name,
                                     b['id'],
                                     b['duration'],
                                     b['result'],
                                     b['url'],
                                     b['result'],
                                     b['url'],
                                     b['id'],
                                     b['duration'],
                                     b['timestamp']))


@click.command()
@click.option('--release', default="master",
              help="the rdo release, e.g. master,ussuri,train")
def main(release="master"):
    print_data(request_data(), release)


if __name__ == '__main__':
    main()
