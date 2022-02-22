#!/usr/bin/env python

import csv
import json
import os
import re
import sys
import time
from datetime import datetime
from io import StringIO
from tempfile import mkstemp

import click
import dlrnapi_client
import requests
import yaml
from dlrnapi_client.rest import ApiException
from jinja2 import Environment, FileSystemLoader
from rich import print as rich_print
from rich.console import Console
from rich.table import Table
from urllib3.exceptions import InsecureRequestWarning

console = Console()

# Use system-provided CA bundle instead of the one installed with pip
# in certifi.
dlrnapi_client.configuration.ssl_ca_cert = ('/etc/pki/ca-trust/extracted/'
                                            'openssl/ca-bundle.trust.crt')


def date_diff_in_seconds(dt2, dt1):
    timedelta = dt2 - dt1

    return timedelta.days * 24 * 3600 + timedelta.seconds


def dhms_from_seconds(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    return (hours, minutes, seconds)


def strip_date_time_from_string(input_string):
    regex_object = re.compile(r'[\d*-]*\d* [\d*:]*')

    return regex_object.search(input_string).group()


def convert_string_date_object(date_string):
    return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')


def download_file(url):
    requests.packages.urllib3.disable_warnings(
        category=InsecureRequestWarning)
    response = requests.get(url, stream=True, verify=False)
    response.raise_for_status()
    file_descriptor, path = mkstemp(prefix="job-output-")
    with open(path, "wb") as file:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                file.write(chunk)
    os.close(file_descriptor)

    return path


def delete_file(path):
    os.remove(path)


def find_job_run_time(url):
    try:
        path = download_file(url + "/job-output.txt")
    except requests.exceptions.RequestException:
        return "N/A"
    with open(path, "r") as file:
        first_line = file.readline()
        for last_line in file:
            pass
    start_time = strip_date_time_from_string(first_line)
    start_time_ob = convert_string_date_object(start_time)
    end_time = strip_date_time_from_string(last_line)
    end_time_ob = convert_string_date_object(end_time)

    hours, minutes, seconds = dhms_from_seconds(
        date_diff_in_seconds(end_time_ob, start_time_ob))
    delete_file(path)

    return f"{hours} hr {minutes} mins {seconds} secs"


def find_failure_reason(url):
    try:
        path = download_file(url + "/logs/failures_file")
    except requests.exceptions.RequestException:
        return "N/A"
    with open(path, "r") as file:
        first_line = file.readline()
    delete_file(path)

    return first_line.rstrip()


def web_scrape(url):
    try:
        requests.packages.urllib3.disable_warnings(
            category=InsecureRequestWarning)
        response = requests.get(url, verify=False)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err)
    except requests.exceptions.RequestException as error:
        raise SystemExit(error)

    return response.text


def url_response_in_yaml(url):
    text_response = web_scrape(url)
    processed_data = yaml.safe_load(text_response)

    return processed_data


def gather_basic_info_from_criteria(url):
    criteria_content = url_response_in_yaml(url)
    api_url = criteria_content['api_url']
    base_url = criteria_content['base_url']

    return api_url, base_url


def find_jobs_in_integration_criteria(url, promotion_name='current-tripleo'):
    criteria_content = url_response_in_yaml(url)

    return criteria_content['promotions'][promotion_name]['criteria']


def find_jobs_in_component_criteria(url, component):
    criteria_content = url_response_in_yaml(url)

    return criteria_content['promoted-components'][component]


def fetch_hashes_from_commit_yaml(url):
    """
    This function finds commit hash, distro hash, extended_hash from commit.yaml
    :param url for commit.yaml
    :returns strings for commit_hash, distro_hash, extended_hash
    """
    commit_yaml_content = url_response_in_yaml(url)
    commit_hash = commit_yaml_content['commits'][0]['commit_hash']
    distro_hash = commit_yaml_content['commits'][0]['distro_hash']
    extended_hash = commit_yaml_content['commits'][0]['extended_hash']

    return commit_hash, distro_hash, extended_hash


def find_results_from_dlrn_agg(api_url, test_hash):
    api_client = dlrnapi_client.ApiClient(host=api_url)
    api_instance = dlrnapi_client.DefaultApi(api_client)
    params = dlrnapi_client.AggQuery(aggregate_hash=test_hash)
    api_response = api_instance.api_agg_status_get(params=params)

    return api_response


def format_ts_from_last_modified(ts, pattern='%a, %d %b %Y %H:%M:%S %Z'):
    ts = datetime.strptime(ts, pattern)
    return int(time.mktime(ts.timetuple()))


# get the date of the consistent link in dlrn
def get_consistent(url, component=None):
    if "centos7" not in url:
        dlrn_tag = "/promoted-components"
        short_url = url.split("/")[:-5]
    else:
        dlrn_tag = "/consistent"
        short_url = url.split("/")[:-3]
    short_url = "/".join(short_url)

    if component is None:
        # integration build, use last promoted_components date
        response = requests.get(short_url + dlrn_tag + '/delorean.repo')
        if response.ok:
            cd = response.headers['Last-Modified']
            consistent_date = format_ts_from_last_modified(cd)
        else:
            return None
    else:
        # TO-DO normalize component and intergration config
        short_url = (short_url + '/component/'
                     + component + '/consistent/delorean.repo')
        response = requests.get(short_url)
        if response.ok:
            cd = response.headers['Last-Modified']
            consistent_date = format_ts_from_last_modified(cd)
        else:
            return None

    return consistent_date


def get_dlrn_versions_csv(base_url, component, tag):
    if component:
        control_tag = "{}/component/{}/{}/versions.csv".format(base_url,
                                                               component,
                                                               tag)
    else:
        control_tag = "{}/{}/versions.csv".format(base_url,
                                                  tag)
    return control_tag


def get_csv(url):
    response = requests.get(url)
    if response.ok:
        content = response.content.decode('utf-8')
        f = StringIO(content)
        reader = csv.reader(f, delimiter=',')
        return [content, reader]


def get_diff(component, control_tag, file1, test_tag, file2):
    # compare the raw string
    if file1[0] == file2[0]:
        return False
    else:
        # for the line by line diff, use csv content
        table = Table(show_header=True, header_style="bold")
        table.add_column(control_tag, style="dim", width=85)
        table.add_column(test_tag, style="dim", width=85)
        for f1, f2 in zip(file1[1], file2[1]):
            if f1 != f2:
                table.add_row(str(f1[9]), str(f2[9]))
        return table


def get_dlrn_promotions(api_url,
                        promotion_name,
                        aggregate_hash=None,
                        commit_hash=None,
                        distro_hash=None,
                        component=None):
    api_client = dlrnapi_client.ApiClient(host=api_url)
    api_instance = dlrnapi_client.DefaultApi(api_client)
    query = dlrnapi_client.PromotionQuery(limit=1,
                                          promote_name=promotion_name)
    if component:
        query.component = component
    pr = api_instance.api_promotions_get_with_http_info(query)[0][0]
    consistent = get_consistent(pr.repo_url, component)
    promotion = {}
    promotion = pr.to_dict()
    promotion['lastest_build'] = consistent
    return promotion


def find_results_from_dlrn_repo_status(api_url, commit_hash,
                                       distro_hash, extended_hash):
    """ This function returns api_response from dlrn for a particular
        commit_hash, distro_hash, extended_hash.
        https://github.com/softwarefactory-project/dlrnapi_client/blob/master/
        docs/DefaultApi.md#api_repo_status_get

        :param api_url: the dlrn api endpoint for a particular release
        :param commit_hash: For a particular repo, commit.yaml contains this
         info.
        :param distro_hash: For a particular repo, commit.yaml contains this
         info.
        :param extended_hash: For a particular repo, commit.yaml contains this
         info.
        :return api_response: from dlrnapi server containing result of
         passing/failing jobs
    """
    if extended_hash == "None":
        extended_hash = None
    api_client = dlrnapi_client.ApiClient(host=api_url)
    api_instance = dlrnapi_client.DefaultApi(api_client)
    params = dlrnapi_client.Params2(commit_hash=commit_hash,
                                    distro_hash=distro_hash,
                                    extended_hash=extended_hash)
    try:
        api_response = api_instance.api_repo_status_get(params=params)
    except ApiException as err:
        print("Exception when calling DefaultApi->api_repo_status_get:"
              " %s\n" % err)
    return api_response


def conclude_results_from_dlrn(api_response):
    passed_jobs = set()
    all_jobs_result_available = set()
    for job in api_response:
        all_jobs_result_available.add(job.job_id)
        if job.success:
            passed_jobs.add(job.job_id)

    failed_jobs = all_jobs_result_available.difference(passed_jobs)

    return all_jobs_result_available, passed_jobs, failed_jobs


def get_job_history(job_name, zuul, component=None):
    if 'rdo' in zuul or 'redhat' in zuul:
        url = zuul + "?job_name={}".format(job_name)

    else:
        # upstream
        upstream_job = job_name.split("-")
        # remove periodic-
        del upstream_job[0]
        # remove -branch
        del upstream_job[-1]
        if component:
            # component jobs remove both -master and -component
            del upstream_job[-1]

        upstream_job = '-'.join([str(elem) for elem in upstream_job])
        url = zuul + "?job_name={}".format(upstream_job)

    out = json.loads(web_scrape(url))

    # key job_name, value = { SUCCESS: count,
    #                         FAILURE: count,
    #                         OTHER: count}
    job_history = {}
    job_history[job_name] = {'SUCCESS': 0, 'FAILURE': 0, 'OTHER': 0}
    limit = 5
    for index, execution in enumerate(out):
        if index == limit:
            break
        if execution['result'] == "SUCCESS":
            job_history[job_name]['SUCCESS'] += 1
        elif execution['result'] == "FAILURE":
            job_history[job_name]['FAILURE'] += 1
        else:
            job_history[job_name]['OTHER'] += 1

    return job_history


def latest_job_results_url(api_response, all_jobs):
    logs_job = {}
    for particular_job in all_jobs:
        latest_log = {}
        for job in api_response:
            if job.job_id == particular_job:
                latest_log[job.timestamp] = job.url
        logs_job[particular_job] = latest_log[max(latest_log.keys())]

    return logs_job


def print_a_set_in_table(input_set, header="Job name"):
    table = Table(show_header=True, header_style="bold")
    table.add_column(header, style="dim", width=80)
    for job in input_set:
        table.add_row(job)
    console.print(table)


def print_failed_in_criteria(input_set,
                             config,
                             stream,
                             compare_upstream,
                             header="Job name",
                             component=None):

    table = Table(show_header=True, header_style="bold")
    table.add_column(header, width=80)
    table.add_column("Integration PASSED History", width=15)
    table.add_column("Integration FAILURE History", width=15)
    table.add_column("Integration Other History", width=15)
    if compare_upstream:
        table.add_column("Upstream PASSED History", width=10)
        table.add_column("Upstream FAILURE History", width=10)
        table.add_column("Upstream Other History", width=10)
    for job in input_set:
        int_history = get_job_history(job,
                                      config[stream]['periodic_builds_url'],
                                      component)
        if compare_upstream:
            upstream_builds_url = config[stream]['upstream_builds_url']
            # do not look for ovb jobs in upstream
            if "featureset" not in job:
                up_history = get_job_history(job,
                                             upstream_builds_url,
                                             component)
                table.add_row(job,
                              str(int_history[job]['SUCCESS']),
                              str(int_history[job]['FAILURE']),
                              str(int_history[job]['OTHER']),
                              str(up_history[job]['SUCCESS']),
                              str(up_history[job]['FAILURE']),
                              str(up_history[job]['OTHER']))
        else:
            table.add_row(job,
                          str(int_history[job]['SUCCESS']),
                          str(int_history[job]['FAILURE']),
                          str(int_history[job]['OTHER']))
    console.print(table)


def load_conf_file(config_file, key):
    config = {}
    with open(config_file, "r") as file:
        config = yaml.safe_load(file)
    return config


def influxdb_jobs(jobs_result):
    # https://docs.influxdata.com/influxdb/v2.0/reference/syntax/line-protocol/
    # jobs_result = the measurement
    # job_type is a tag, note the space
    # rest of the values are fields in a row of data

    # grafana can only color code w/ numbers, not text
    # 0 = failed, 5 = pending, 9 = success # grafana thresholds.
    if jobs_result['status'] == "failed":
        jobs_result['status'] = 0
    elif jobs_result['status'] == "pending":
        jobs_result['status'] = 5
    elif jobs_result['status'] == "passed":
        jobs_result['status'] = 9

    results_influxdb_line = ('jobs_result,'
                             'job_type={job_type},'
                             'job_name={job},'
                             'release={release} '
                             'name="{promote_name}",'
                             'test_hash="{test_hash}",'
                             'criteria="{criteria}",'
                             'status="{status}",'
                             'logs="{logs}",'
                             'failure_reason="{failure_reason}",'
                             'duration="{duration}",'
                             'component="{component}",'
                             'distro="{distro}"')

    if jobs_result['component'] is None:
        jobs_result['job_type'] = "integration"
    else:
        jobs_result['job_type'] = "component"
    return results_influxdb_line.format(**jobs_result)


def influxdb_promo(promotion):
    # grafana renders epoch only w/ * 1000
    gr_promotion_date = str(int(promotion['timestamp']) * 1000000000)
    gr_latest_build = str(int(promotion['lastest_build']) * 1000)
    promotion['grafana_timestamp'] = gr_promotion_date
    promotion['grafana_latest_build'] = gr_latest_build
    promotion_influxdb_line = ("dlrn-promotion,"
                               "release={release},distro={distro},"
                               "promo_name={promote_name} "
                               "commit_hash=\"{commit_hash}\","
                               "distro_hash=\"{distro_hash}\","
                               "aggregate_hash=\"{aggregate_hash}\","
                               "repo_hash=\"{repo_hash}\","
                               "repo_url=\"{repo_url}\","
                               "latest_build_date={grafana_latest_build},"
                               "component=\"{component}\","
                               "promotion_details=\"{dlrn_details}\","
                               "extended_hash=\"{extended_hash}\" "
                               "{grafana_timestamp}")
    return promotion_influxdb_line.format(**promotion)


def render_testproject_yaml(jobs, hash, stream, config):
    jobs_list = jobs
    path = os.path.dirname(__file__)
    file_loader = FileSystemLoader(path + '/templates')
    env = Environment(loader=file_loader)
    template = env.get_template('.zuul.yaml.j2')
    output = template.render(jobs=jobs_list, hash=hash)
    print("\n\n###### testproject to rerun required jobs ######")
    print(config[stream]['testproject_url'] + "\n")
    print(output)


def track_integration_promotion(args, config):

    distro = args['distro']
    release = args['release']
    aggregate_hash = args['aggregate_hash']
    influx = args['influx']
    stream = args['stream']
    compare_upstream = args['compare_upstream']
    promotion_name = args['promotion_name']

    url = config[stream]['criteria'][distro][release]['int_url']
    dlrn_api_url, dlrn_trunk_url = gather_basic_info_from_criteria(url)
    promotions = get_dlrn_promotions(dlrn_api_url, promotion_name)
    if distro != "centos-7":
        md5sum_url = dlrn_trunk_url + aggregate_hash + '/delorean.repo.md5'
        test_hash = web_scrape(md5sum_url)
        api_response = find_results_from_dlrn_agg(dlrn_api_url, test_hash)

    else:
        commit_url = dlrn_trunk_url + aggregate_hash + '/commit.yaml'
        commit_hash, distro_hash, extended_hash = fetch_hashes_from_commit_yaml(
                                                    commit_url)
        api_response = find_results_from_dlrn_repo_status(dlrn_api_url,
                                                          commit_hash,
                                                          distro_hash,
                                                          extended_hash)
        test_hash = commit_hash

    (all_jobs_result_available,
     passed_jobs, failed_jobs) = conclude_results_from_dlrn(api_response)
    jobs_in_criteria = set(find_jobs_in_integration_criteria(
        url, promotion_name=promotion_name))
    jobs_which_need_pass_to_promote = jobs_in_criteria.difference(passed_jobs)
    jobs_with_no_result = jobs_in_criteria.difference(all_jobs_result_available)
    all_jobs = all_jobs_result_available.union(jobs_with_no_result)

    # get the dlrn details, hash under test ( hut ) and promoted hash ( ph )
    if distro != "centos-7":
        dlrn_api_suffix = "api/civotes_agg_detail.html?ref_hash="
        # hash under test
        hut = "{}/{}{}".format(dlrn_api_url,
                               dlrn_api_suffix,
                               test_hash)
        # promoted hash
        ph = "{}/{}{}".format(dlrn_api_url,
                              dlrn_api_suffix,
                              promotions['aggregate_hash'])

    else:
        dlrn_api_suffix = "api/civotes_detail.html?commit_hash="
        # hash under test
        hut = "{}/{}{}&distro_hash={}".format(dlrn_api_url,
                                              dlrn_api_suffix,
                                              commit_hash,
                                              distro_hash)
        # promoted hash
        ph = "{}/{}{}&distro_hash={}".format(dlrn_api_url,
                                             dlrn_api_suffix,
                                             promotions['commit_hash'],
                                             promotions['distro_hash'])
    if influx:
        # NOTE(dviroel): excluding jobs results from influx when promotion_name
        #  is "current-tripleo-rdo" since we are not using this info anywhere.
        if promotion_name != 'current-tripleo-rdo':
            # print out jobs in influxdb format
            log_urls = latest_job_results_url(
                api_response, all_jobs_result_available)
            for job in all_jobs:
                log_url = log_urls.get(job, "N/A")
                if job in passed_jobs:
                    status = 'passed'
                elif job in failed_jobs:
                    status = 'failed'
                else:
                    status = 'pending'
                if status == 'failed':
                    failure_reason = find_failure_reason(log_url)
                else:
                    failure_reason = "N/A"
                jobs_result = {}
                jobs_result['release'] = release
                jobs_result['promote_name'] = promotion_name
                jobs_result['job'] = job
                jobs_result['test_hash'] = test_hash
                jobs_result['component'] = None
                jobs_result['criteria'] = job in jobs_in_criteria
                jobs_result['status'] = status
                jobs_result['logs'] = log_url
                jobs_result['failure_reason'] = failure_reason
                jobs_result['duration'] = find_job_run_time(
                    log_url)
                jobs_result['distro'] = distro
                print(influxdb_jobs(jobs_result))

        # print out last promotions in influxdb format
        promotions['release'] = release
        promotions['distro'] = distro
        promotions['dlrn_details'] = ph
        print(influxdb_promo(promotions))
    else:
        last_p = datetime.utcfromtimestamp(promotions['timestamp'])
        console.print(f"Hash under test: {hut}",
                      f"\nlast_promotion={last_p}")
        print_a_set_in_table(passed_jobs, "Jobs which passed:")
        print_a_set_in_table(failed_jobs, "Jobs which failed:")
        print_a_set_in_table(jobs_with_no_result,
                             "Pending running jobs")
        needed_txt = ("Jobs which are in promotion criteria and need "
                      "pass to promote the Hash:")

        print_failed_in_criteria(jobs_which_need_pass_to_promote,
                                 config,
                                 stream,
                                 compare_upstream,
                                 needed_txt)
        console.print("Logs of jobs which are failing:-")
        log_urls = latest_job_results_url(
            api_response, failed_jobs)
        for value in log_urls.values():
            console.print(value)

        # get package diff for the integration test
        # control_url
        c_url = get_dlrn_versions_csv(dlrn_trunk_url,
                                      None,
                                      promotion_name)
        # test_url, what is currently getting tested
        t_url = get_dlrn_versions_csv(dlrn_trunk_url,
                                      None,
                                      aggregate_hash)
        c_csv = get_csv(c_url)
        t_csv = get_csv(t_url)
        pkg_diff = get_diff(None,
                            promotion_name,
                            c_csv,
                            aggregate_hash,
                            t_csv)
        if pkg_diff:
            console.print("\n Packages Tested")
            rich_print(pkg_diff)

        # jobs_which_need_pass_to_promote are any job that hasn't registered
        # success w/ dlrn.  jobs_with_no_result are any jobs in pending.
        # We only want test project config for jobs that have completed.
        tp_jobs = jobs_which_need_pass_to_promote - jobs_with_no_result
        if tp_jobs:
            render_testproject_yaml(tp_jobs, test_hash, stream, config)


def track_component_promotion(cargs, config):
    """ Find the failing jobs which are blocking promotion of a component.
    :param release: The OpenStack release e.g. wallaby
    :param component:
    """
    distro = cargs['distro']
    release = cargs['release']
    influx = cargs['influx']
    test_component = cargs['component']
    stream = cargs['stream']
    compare_upstream = cargs['compare_upstream']

    url = config[stream]['criteria'][distro][release]['comp_url']
    dlrn_api_url, dlrn_trunk_url = gather_basic_info_from_criteria(url)

    if distro == "centos-7":
        raise Exception("centos-7 components do not exist")

    if test_component == "all":
        all_components = ["baremetal", "cinder", "clients", "cloudops",
                          "common", "compute", "glance", "manila",
                          "network", "octavia", "security", "swift",
                          "tempest", "tripleo", "ui", "validation"]
        pkg_diff = None
    else:
        all_components = [test_component]
        # get package diff for the component
        # control_url
        c_url = get_dlrn_versions_csv(dlrn_trunk_url,
                                      all_components[0],
                                      "current-tripleo")
        # test_url, what is currently getting tested
        t_url = get_dlrn_versions_csv(dlrn_trunk_url,
                                      all_components[0],
                                      "component-ci-testing")
        c_csv = get_csv(c_url)
        t_csv = get_csv(t_url)
        pkg_diff = get_diff(all_components[0],
                            "current-tripleo",
                            c_csv,
                            "component-ci-testing",
                            t_csv)

    for component in all_components:
        commit_url = '{}component/{}/component-ci-testing/commit.yaml'.format(
                          dlrn_trunk_url, component)
        commit_hash, distro_hash, extended_hash = fetch_hashes_from_commit_yaml(
                                                    commit_url)
        api_response = find_results_from_dlrn_repo_status(dlrn_api_url,
                                                          commit_hash,
                                                          distro_hash,
                                                          extended_hash)

        # component promotion details
        promotions = get_dlrn_promotions(dlrn_api_url,
                                         "promoted-components",
                                         component=component)

        dlrn_api_suffix = "api/civotes_detail.html?commit_hash="
        # hash under test
        hut = "{}/{}{}&distro_hash={}".format(dlrn_api_url,
                                              dlrn_api_suffix,
                                              commit_hash,
                                              distro_hash)
        ph = "{}/{}{}&distro_hash={}".format(dlrn_api_url,
                                             dlrn_api_suffix,
                                             promotions['commit_hash'],
                                             promotions['distro_hash'])
        (all_jobs_result_available,
         passed_jobs, failed_jobs) = conclude_results_from_dlrn(api_response)
        if 'consistent' in all_jobs_result_available:
            all_jobs_result_available.remove('consistent')
        if 'consistent' in passed_jobs:
            passed_jobs.remove('consistent')
        if 'consistent' in failed_jobs:
            failed_jobs.remove('consistent')
        jobs_in_criteria = set(find_jobs_in_component_criteria(url, component))
        jobs_which_need_pass_to_promote = jobs_in_criteria.difference(
                                            passed_jobs)
        jobs_with_no_result = jobs_in_criteria.difference(
            all_jobs_result_available)
        all_jobs = all_jobs_result_available.union(jobs_with_no_result)
        if influx:
            log_urls = latest_job_results_url(
                api_response, all_jobs_result_available)
            for job in all_jobs:
                log_url = log_urls.get(job, "N/A")
                if job in passed_jobs:
                    status = 'passed'
                elif job in failed_jobs:
                    status = 'failed'
                else:
                    status = 'pending'
                if status == 'failed':
                    failure_reason = find_failure_reason(log_url)
                else:
                    failure_reason = "N/A"
                jobs_result = {}
                jobs_result['release'] = release
                jobs_result['promote_name'] = "promoted-components"
                jobs_result['job'] = job
                jobs_result['test_hash'] = commit_hash + '_' + distro_hash[0:8]
                jobs_result['component'] = component
                jobs_result['criteria'] = job in jobs_in_criteria
                jobs_result['status'] = status
                jobs_result['logs'] = log_url
                jobs_result['failure_reason'] = failure_reason
                jobs_result['duration'] = find_job_run_time(
                    log_url)
                jobs_result['distro'] = distro
                # print out jobs in influxdb format
                print(influxdb_jobs(jobs_result))

                # print out promtions in influxdb format
                promotions['release'] = release
                promotions['distro'] = distro
                promotions['dlrn_details'] = ph
                print(influxdb_promo(promotions))
        else:
            log_urls = latest_job_results_url(
                api_response, failed_jobs)
            header = ("{} component jobs which need pass to promote "
                      "the hash: ").format(component)
            if failed_jobs:
                component_status = "Red"
            elif not jobs_which_need_pass_to_promote:
                component_status = "Green"
            else:
                component_status = "Yellow"
            last_p = datetime.utcfromtimestamp(promotions['timestamp'])
            console.print(f"{component} component",
                          f"status={component_status}",
                          f"last_promotion={last_p}",
                          f"\nHash_under_test={hut}")

            print_a_set_in_table(passed_jobs, "Jobs which passed:")
            if component_status != "Green":
                print_a_set_in_table(failed_jobs, "Jobs which failed:")
                print_a_set_in_table(jobs_with_no_result,
                                     "Pending running jobs")
                print_failed_in_criteria(jobs_which_need_pass_to_promote,
                                         config,
                                         stream,
                                         compare_upstream,
                                         header,
                                         component)
                if component_status == "Red":
                    console.print("Logs of failing jobs:")
                    for value in log_urls.values():
                        console.print(value)

            if pkg_diff:
                console.print("\nPackages Tested: {}".format(all_components[0]))
                rich_print(pkg_diff)
            print('\n')

            # jobs_which_need_pass_to_promote are any job that hasn't registered
            # success w/ dlrn.  jobs_with_no_result are any jobs in pending.
            # We only want test project config for jobs that have completed.
            tp_jobs = jobs_which_need_pass_to_promote - jobs_with_no_result
            # execute if there are failing jobs in criteria and if
            # you are only looking at one component and not all components
            if tp_jobs and len(all_components) == 1:
                render_testproject_yaml(tp_jobs, commit_hash, stream, config)


@ click.command()
@ click.option("--release", default='master',
               type=click.Choice(['master', 'wallaby', 'victoria', 'ussuri',
                                  'train', 'stein', 'queens', 'osp17',
                                  'osp16-2']))
@ click.option("--distro", default='centos-8',
               type=click.Choice(['centos-8', 'centos-9', 'centos-7',
                                  'rhel-8', 'rhel-9']))
@ click.option("--component",
               type=click.Choice(["all", "baremetal", "cinder", "clients",
                                  "cloudops", "common", "compute",
                                  "glance", "manila", "network", "octavia",
                                  "security", "swift", "tempest", "tripleo",
                                  "ui", "validation"]))
@ click.option("--influx", is_flag=True, default=False)
@ click.option("--compare_upstream", is_flag=True, default=False)
@ click.option("--aggregate_hash",
               required=False,
               default="tripleo-ci-testing",
               # TO-DO w/ tripleo-get-hash
               help=("default:tripleo-ci-testing"
                     "\nexample:tripleo-ci-testing/e6/ad/e6ad..."))
@ click.option("--promotion_name", required=False, default="current-tripleo",
               type=click.Choice(["current-tripleo", "current-tripleo-rdo"]))
@ click.option("--config_file", default=os.path.dirname(__file__)
               + '/conf_ruck_rover.yaml')
def main(release,
         distro,
         config_file,
         influx=False,
         component=None,
         compare_upstream=False,
         aggregate_hash="tripleo-ci-testing",
         promotion_name="current-tripleo"):

    if release in ('osp16-2', 'osp17'):
        stream = 'downstream'
        if config_file != os.path.dirname(__file__) + '/conf_ruck_rover.yaml':
            print('using custom config file: {}'.format(config_file))
        else:
            downstream_urls = 'https://url.corp.redhat.com/ruck-rover-0'
            config_file = download_file(downstream_urls)
        config = load_conf_file(config_file, "downstream")
    else:
        config = load_conf_file(config_file, "upstream")
        stream = 'upstream'

    # come on click, not sure how to get click params.
    c_args = {}
    for i in dir():
        # fix-me eval
        c_args[i] = eval(i)  # pylint: disable=eval-used
        c_args["stream"] = stream

    if release in ('stein', 'queens'):
        config['distro'] = "centos-7"

    if release == 'osp16-2':
        config['distro'] = "rhel-8"
        c_args['distro'] = "rhel-8"

    # prompt user: #osp-17 can be rhel-8 or rhel-9
    if release == 'osp17' and distro == 'centos-8':
        print("\nOSP-17 can be either --distro rhel-8 or --distro rhel-9")
        print("ERROR: please set the distro option on the cli")
        sys.exit(1)

    if component:
        track_component_promotion(c_args, config)
    else:
        track_integration_promotion(c_args, config)


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter
