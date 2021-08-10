#!/usr/bin/python3

import click
import requests


def request_data(jenkins_url):
    jenkins_query = ("?tree=jobs[name,builds[fullDisplayName,id,url,"
                     + "logs,number,timestamp,duration,result]]"
                     + "&xpath=/hudson/job/build"
                     + "[count(result)=0]&wrapper=builds")

    r = requests.get(jenkins_url + "/api/json" + jenkins_query, verify=False)
    return r


def print_data(data, release, name_filter):

    jobs = data.json()['jobs']

    for j in jobs:
        if 'builds' in j.keys():
            job_name = j['name']
        # hard code filter on master-promote jobs
        if name_filter in job_name:
            if release in job_name:
                for b in j['builds']:
                    b['timestamp'] = int(b['timestamp'] * 1000000)
                    if b['result'] == "SUCCESS":
                        b['result_int'] = int(1)
                    else:
                        b['result_int'] = int(0)
                    # convert milliseconds to seconds
                    b['duration'] = round(int(b['duration']) / 1000)
                    print(('jenkins,'
                           'job_name={},build_id="{}",'
                           'duration={},result="{}",'
                           'url="{}" result="{}",'
                           'url="{}",build_id="{}",'
                           'result_int={},'
                           'duration={} {}').
                          format(job_name,
                                 b['id'],
                                 b['duration'],
                                 b['result'],
                                 b['url'],
                                 b['result'],
                                 b['url'],
                                 b['id'],
                                 b['result_int'],
                                 b['duration'],
                                 b['timestamp']))


@click.command()
@click.option('--release', default="master",
              help="the rdo release, e.g. master,ussuri,train")
@click.option('--name_filter', default="tripleo-quickstart",
              help="filter out jobs with a keyword")
@click.option('--jenkins_url',
              default="https://jenkins-cloudsig-ci.apps.ocp.ci.centos.org/",
              help="base url of jenkins server")
def main(release="master",
         name_filter="tripleo-quickstart",
         jenkins_url="https://jenkins-cloudsig-ci.apps.ocp.ci.centos.org/"):

    print_data(request_data(jenkins_url), release, name_filter)


if __name__ == '__main__':
    main()
