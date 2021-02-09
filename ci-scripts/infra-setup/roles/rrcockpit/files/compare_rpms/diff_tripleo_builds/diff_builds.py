#!/usr/bin/env python3

import logging
import re
import urllib
from collections import defaultdict

import click
import requests
from bs4 import BeautifulSoup
from cachecontrol import CacheControl
from prettytable import PrettyTable
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from toolchest.rpm import rpmvercmp, utils

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class DiffBuilds(object):

    def __fetch_container_directory_list(self, base_url, node):
        containers_url = ("{}/{}/var/log/extra/podman/"
                          "containers/".format(base_url, node))
        page = requests.get(containers_url).content
        return [page, containers_url]

    def __parse_container_directory_list(self, html_page):
        page = html_page[0]
        containers_url = html_page[1]
        soup = BeautifulSoup(page, 'html.parser')
        table = soup.find('table')
        try:
            rows = table.findAll('tr')
        except Exception:
            this_error = ("(A list of containers was not found "
                          "at: {})".format(containers_url))
            logging.error(this_error)
            logging.warning("Try using the -a option for a repoquery")
            raise Exception(this_error)
        containers = []
        for tr in rows:
            logging.debug(tr)
            if tr.find('a'):
                full_link = tr.find('a').get('href')
                dirty_link = re.match(r'^\.', full_link)
                index_link = re.match(r'.*\/index.html', full_link)
                if index_link:
                    # container_name/index.html
                    container_name = full_link[:-11]
                elif dirty_link:
                    # ./container_name/
                    container_name = full_link[2:-1]
                else:
                    # container_name/
                    container_name = full_link[:-1]
                is_alpha = re.match('[a-zA-Z]', container_name[0:4])
                if is_alpha:
                    containers.append(container_name)
        return containers

    def get_directory_list(self, base_url, node):
        """
        Gets the directory listing of the directory

        Get's all the href a links from beautifulsoup
        to create a list of containers. Remove any
        href a links that are not a real container dir.

        Parameters:
        url (string): base url passed
        node (string): the node type

        Returns:
        list: a list of ALL the directories in the containers dir
        """
        page = self.__fetch_container_directory_list(base_url, node)
        containers = self.__parse_container_directory_list(page)
        return containers

    def process_containers(self, cache, base_url, node, containers_list):
        """
        break this into two parts for better unit testing
        """
        containers_strings = self.process_containers_step1(cache,
                                                           base_url,
                                                           node,
                                                           containers_list)
        dict_of_containers = self.process_containers_step2(containers_strings)
        return dict_of_containers

    def process_containers_step1(self, cache, base_url, node, containers_list):
        """
        Pull the podman_info file and scrape out rpm info

        Get each podman_info file tries .txt and .txt.gz
        Process the string to return the rpms.

        Parameters:
        cache: (object) requests caching object
        base_url (string): base url passed
        node (string): the node type
        containers_list (list) list of container names

        Returns:
        dict_of_containers: (dict) keyname package, value = rpm version
        """
        dict_of_containers = {}
        if containers_list == []:
            logging.warning(
                "containers were not logged for: {}".format(base_url))
            return dict_of_containers
        containers_list.pop(0)
        for c in containers_list:
            logging.info("processing {} containers: {}".format(node, c))
            # for podman_info_log.txt, .gz, .txt.gz
            url = ("{}/{}/var/log/extra/podman/containers/{}/podman_info.log"
                   .format(base_url, node, c))
            req = cache.get(url, verify=False)
            if req.status_code == 200:
                container_info_temp = str(req.content.decode('UTF-8'))
            else:
                url = ("{}/{}/var/log/extra/podman/containers/{}"
                       "/podman_info.log.txt.gz".format(base_url, node, c))
                req = cache.get(url, verify=False)
                if req.status_code == 200:
                    container_info_temp = str(req.content.decode('UTF-8'))
                else:
                    url = ("{}/{}/var/log/extra/podman/containers/{}"
                           "/podman_info.log.gz".format(base_url, node, c))
                    req = cache.get(url, verify=False)
                    if req.status_code == 200:
                        container_info_temp = str(req.content.decode('UTF-8'))
                    else:
                        this_error = "request failed to fetch: {}".format(url)
                        raise Exception(this_error)

            if "Installed Packages" in container_info_temp:
                container_name = c[:-1]
                container_info_temp = container_info_temp.partition(
                    "Installed Packages")[2].split("\n")
                container_info_temp.pop(0)
                dict_of_containers[container_name] = container_info_temp
        return dict_of_containers

    def process_containers_step2(self, dict_of_containers):
        for container_name, value in dict_of_containers.items():
            container_info = []
            for counter, i in enumerate(value):
                # remove .x86_64
                try:
                    parts = i.split(" ")
                    # rpms can be logged to multiple lines
                    # the length of a full line should be three
                    is_alpha = re.match('[a-zA-Z]', parts[0])
                    if len(parts) > 1 and is_alpha:
                        nvr = "{}-{}".format(i.strip().split()[0][:-7],
                                             i.strip().split()[1])
                        container_info.append(nvr)
                    else:
                        # rpm info on more than one line
                        if len(parts) == 1 and is_alpha:
                            name = i[:-7]
                            version = value[counter + 1].strip().split(" ")[0]
                            nvr = "{}-{}".format(name, version)
                            container_info.append(nvr)
                except IndexError:
                    if str(i) != "":
                        logging.warning("Index Error found on\
                                        (ignore empty): " + str(i))
            dict_of_containers[container_name] = container_info
        return dict_of_containers

    def get_repoquery_logs(self, cache, base_url, node):
        """
        In cases where the container logs are not available, use repoquery

        Some CI jobs do not have the container logs.  A file in
        /var/log/extra/all_available_packages.txt should be present that
        is a repoquery of all enabled yum repos on the node.

        Parameters:
        cache (object): requests cache object
        base_url (string): base url passed
        node (string): the node type

        Returns:
        list: a list of rpms
        """
        url = "{}/{}/var/log/extra/all_available_packages.txt".format(
            base_url, node)
        list = cache.get(url, verify=False)
        if list.status_code != 200:
            url = "{}/{}/var/log/extra/all_available_packages.txt.gz".format(
                base_url, node)
            list = cache.get(url, verify=False)
            if list.status_code != 200:
                repoquery_not_avail = ("logs for base node {} were NOT "
                                       "available: {}".format(node, url))
                raise Exception(repoquery_not_avail)
        nice_list = list.content.decode('UTF-8').splitlines()
        return nice_list

    def json_extract(self, obj, key):
        """
        extract values from nested JSON.

        Parameters:
            obj (object): json object
            key (string): key from json converted to a dict.
        """
        arr = []

        def extract(obj, arr, key):
            """Recursively search for values of key in JSON tree."""
            if isinstance(obj, dict):
                for k, v in obj.items():
                    # print("key: {} value: {}".format(k, v))
                    if isinstance(v, (dict, list)):
                        extract(v, arr, key)
                    elif k == key:
                        arr.append(v)
            elif isinstance(obj, list):
                for item in obj:
                    extract(item, arr, key)
            return arr

        values = extract(obj, arr, key)
        return values

    def get_compose_logs(self, cache, base_url):
        """
        Go to the source and diff two compose builds

        Using the path to the compose as the baseurl
        e.g...  16.x/RHOS_foo/compose
        then tack on the build info
        metadata/rpms.json

        Parameters:
        cache (object): requests cache object
        base_url (string): base url passed

        Returns:
        list: a list of rpms
        """
        url = "{}/metadata/rpms.json".format(base_url)
        result = cache.get(url, verify=False)
        if result.status_code != 200:
            compose_not_avail = ("logs for the compose were NOT "
                                 "available: {}".format(url))
            raise Exception(compose_not_avail)
        return result.json()

    def parse_compose(self, json_result):
        result = json_result
        data = result['payload']['rpms']

        rpms_list_in_path = self.json_extract(data, "path")
        nice_list = []
        for i in rpms_list_in_path:
            nice_list.append(i.split("/")[-1])

        return nice_list

    def get_logs(self, cache, base_url, node):
        """
        Gets the rpm logs from the base_url

        base_url should be passed here
        the base node and container rpm lists will be parsed after
        e.g. https://storage.gra.cloud.ovh.net/v1/\
        AUTH_dcaab5e32b234d56b626f72581e3644c/zuul_opendev_logs_a7d/756888/2/\
        gate/tripleo-ci-centos-8-containers-multinode-train/a7d91e1/logs

        Parameters:
        cache (object): requests cachine object
        base_url (string): base url passed
        node (string): the node type

        Returns:
        list: a list of ALL the directories in the containers dir
        """

        # first test if we're using http(s) or local file
        test_url = urllib.parse.urlparse(base_url)
        if test_url.scheme == 'file':
            file_error = "file format is not supported, yet"
            raise Exception(file_error)
        else:
            url = "{}/{}/var/log/extra/rpm-list.txt".format(base_url, node)
            logging.info("processing host node {}".format(node))
            list = cache.get(url, verify=False)
            if list.status_code != 200:
                url = "{}/{}/var/log/extra/rpm-list.txt.gz".format(
                    base_url, node)
                list = cache.get(url, verify=False)
                if list.status_code != 200:
                    logs_not_avail = ("logs for base node {} were NOT "
                                      "available: {}".format(node, url))
                    raise Exception(logs_not_avail)
            nice_list = list.content.decode('UTF-8').splitlines()
        if nice_list:
            # check containers
            containers_list = self.get_directory_list(base_url, node)
            rpms_from_containers = self.process_containers(cache,
                                                           base_url,
                                                           node,
                                                           containers_list)

        nice_list = set(nice_list)
        for k, v in rpms_from_containers.items():
            nice_list.update(v)
            logging.debug("The node {} has {} unique packages".format(
                node, str(len(nice_list))))

        return nice_list

    def parse_list(self, this_list, ignore_packages=None):
        """
        Take a list of containers and convert it to dictionary

        Dictionary key is the package name, the value is the version info

        Parameters:
        list (list): list of rpms

        Returns:
        packages: a dictionary of rpm key, value pairs
        """
        packages = defaultdict(list)
        # TO-DO pass ignored and error to result
        # packages_ignored = ()
        packages_error = ()
        for item in this_list:
            # sanitize
            ignored = False
            if "metadata expiration" in item:
                continue
            try:
                nvr = utils.splitFilename(item)
                # <lon> labelcompare functions expect (epoch, version, release)
                epoch = nvr[3]
                version = nvr[1]
                release = nvr[2]
                if ignore_packages:
                    search_term = "{}".format(nvr[0])
                    for ignore in ignore_packages:
                        if ".*" in ignore:
                            r = re.compile(ignore)
                            match = r.match(search_term)
                            if match:
                                logging.info(
                                    "Ignoring Package: {}".format(search_term))
                                ignored = True
                        else:
                            if ignore in search_term:
                                logging.info(
                                    "Ignoring Package: {}".format(search_term))
                                ignored = True
                if not ignored:
                    packages[nvr[0]].append((epoch, version, release))
            except Exception as e:
                logging.error(e)
                logging.warning(
                    "error found getting package name/version for {}"
                    " OR the ignore package regex {}".format(str(item), ignore))
                is_alpha = re.match('[a-zA-Z]', nvr[0])
                if not is_alpha:
                    packages_error.add(item)
                    logging.warning("package name does not meet criteria "
                                    "for item: {}".format(item))
                    continue
                continue
        return packages

    def find_highest_version(self, packages, cpaas=False):
        """
        Get the highest version of rpms in a list

        This method should be replaced and we should
        use the yum python libraries

        Parameters:
        packages (dict): rpm key value pairs

        Returns:
        dict_of_rpms: dictionary of rpms w/ unique highest versions

        note:
        epoch = nvr[3]
        version = nvr[1]
        release = nvr[2]
        packages[nvr[0]].append((epoch, version, release))
        """
        dict_of_rpms = {}
        for key in packages:

            highest_version_tuple = packages[key][0]
            if not cpaas:
                for item in packages[key]:
                    if rpmvercmp.labelCompare(item,
                                              highest_version_tuple) == 1:
                        highest_version_tuple = item
            else:
                for item in packages[key]:
                    if utils.cpaas_label_compare(item,
                                                 highest_version_tuple) == 1:
                        highest_version_tuple = item

            highest_version = highest_version_tuple[1]
            highest_release = highest_version_tuple[2]
            # if the epoch is []
            if len(highest_version_tuple[0]) == 0:

                highest_full_version = "{}-{}".format(highest_version,
                                                      highest_release)
            else:
                highest_epoch = highest_version_tuple[0]
                highest_full_version = "{}-{}-{}".format(highest_epoch,
                                                         highest_version,
                                                         highest_release)
            dict_of_rpms[key] = [highest_version, highest_full_version]
        return dict_of_rpms

    def diff_packages(self,
                      control_list,
                      test_list,
                      not_found_message="not installed"):
        """
        Create a dict of rpms, key = name, value = ["control", "test"] version

        Parameters:
        control_list (dict): rpm key value pairs
        test_list (dict): rpm key value pairs
        no_diff (boolean): show all rpms

        Returns:
        dict_of_rpms: dictionary of rpms w/ unique highest versions
        """
        package_diff = {}
        control_keys = set(control_list.keys())
        test_keys = set(test_list.keys())
        # rpms found in both control and test
        common_keys = set(control_keys).intersection(set(test_keys))
        # rpms in control only
        in_control_only = control_keys - test_keys
        # rpms in test only
        in_test_only = test_keys - control_keys

        for key in common_keys:
            if control_list[key] != test_list[key]:
                version_list = []
                # add control version to [0]
                version_list.append(control_list[key])
                # add test version to [1]
                version_list.append(test_list[key])
                # add list to dictionary["rpm_name"]
                package_diff[key] = version_list
        for key in in_control_only:
            version_list = []
            version_list.append(control_list[key])
            version_list.append(["0", not_found_message])
            package_diff[key] = version_list
        for key in in_test_only:
            version_list = []
            version_list.append(["0", not_found_message])
            version_list.append(test_list[key])
            package_diff[key] = version_list

        return package_diff

    def check_for_even_nodes(self, nodes, column_list):
        # protect against diffing logs w/o matching node sets
        error = {}
        error['error: node_mismatch'] = nodes
        # False indicates failures, nodes uneven
        even_nodes = [False, error, column_list]

        if nodes['control'].keys() != nodes['test'].keys():
            logging.error("The node types in control and test do not match, "
                          "unable to run diff")
            return even_nodes
        elif not (bool(nodes['control'])) or not (bool(nodes['test'])):
            logging.error(
                "No available nodes found in either control or test")
            return even_nodes
        else:
            logging.info(
                "Nodes on control and test match, proceeding with diff")
            # True indicates nodes are even
            return [True, error, column_list]

    def display_packages_table(self,
                               node,
                               column_list,
                               package_diff,
                               extra_package_data=False,
                               just_return=False,
                               write_table_to_file=False,
                               table_file_location='diff_table.log'):
        """ print a table with rows showing the
        rpm package name, version and optionally,
        realease.
        """
        t = PrettyTable()
        t.field_names = column_list
        t.left_padding_width = 1

        if node == "error: node_mismatch":
            t.add_row([node, "error",
                       package_diff['control'],
                       package_diff['test']
                       ])
        else:
            for package_name in list(package_diff.keys()):
                t.add_row([node,
                           package_name,
                           package_diff[package_name][0][1],
                           package_diff[package_name][1][1]
                           ])
        logging.info("\n{}".format(t.get_string(sortby="Package_Name")))

        if write_table_to_file:
            with open(table_file_location, 'w') as f:
                f.write(t.get_string(sortby="Package_Name"))

    def print_packages(self, name, packages):
        for key in packages:
            print("{} {}:{}".format(name, key, packages[key][1]))

    def get_the_nodes(self,
                      cache,
                      control_url,
                      test_url,
                      all_available,
                      undercloud_only=False):
        # all available packages, not nodes.. confusing.. FIXME
        if all_available:
            just_the_undercloud = True
        elif undercloud_only:
            just_the_undercloud = True
        else:
            just_the_undercloud = False

        logging.info("\nDetecting available nodes:\n")
        urls = {
            'control': control_url,
            'test': test_url
        }
        if just_the_undercloud:
            nodes = {
                'undercloud': ["undercloud", "undercloud-0"]
            }
        else:
            nodes = {
                'undercloud': ["undercloud", "undercloud-0"],
                'controller': ["subnode-1", "overcloud-controller-0",
                               "controller-0"],
                'compute': ["overcloud-novacompute-0", "compute-0"],
                # 'storage': ["", "ceph-0"]
            }

        matching_nodes = {}
        for url_type, url in urls.items():
            url_type_dict = {}
            for k, v in nodes.items():
                for element in enumerate(v):
                    full_url = "{}/{}".format(url, element[1])
                    req = cache.get(full_url, verify=False)
                    if req.status_code == 200:
                        url_type_dict[k] = element[1]
                        logging.debug("SUCCESS: found: {}".format(full_url))
                    else:
                        logging.debug("unable to get url: {}".format(full_url))
            matching_nodes[url_type] = url_type_dict

        logging.info("Found the following nodes:")
        logging.info("matching_nodes: {}\n".format(matching_nodes))
        return matching_nodes

    def execute_installed_package_diff(self,
                                       cache,
                                       control_url,
                                       test_url,
                                       all_available,
                                       ignore_packages,
                                       undercloud_only,
                                       cpaas=False):
        full_package_diff = {}
        logging.info("\n\nThis will compare packages installed on the host and"
                     " rpms installed on each container running on the host\n")
        nodes = self.get_the_nodes(cache,
                                   control_url,
                                   test_url,
                                   all_available,
                                   undercloud_only)
        # TO-DO; include ceph
        # node_list = ["undercloud", "controller", "compute", "ceph"]
        node_list = ["undercloud", "controller", "compute"]
        column_list = ['Node',
                       'Package_Name',
                       'Control Package Version',
                       'Test Package Version']

        even_nodes = self.check_for_even_nodes(nodes, column_list)
        if not even_nodes[0]:
            return [even_nodes[1], column_list]
        for i in node_list:
            if i in nodes['control'].keys():
                control_list = self.get_logs(
                    cache, control_url, nodes['control'][i])
                test_list = self.get_logs(
                    cache, test_url, nodes['test'][i])
                control_list = self.parse_list(control_list, ignore_packages)
                test_list = self.parse_list(test_list, ignore_packages)

                control_list = self.find_highest_version(control_list, cpaas)
                test_list = self.find_highest_version(test_list, cpaas)

                package_diff = self.diff_packages(control_list,
                                                  test_list)
                full_package_diff[i] = package_diff

        return [full_package_diff, column_list]

    def execute_repoquery_diff(self,
                               cache,
                               control_url,
                               test_url,
                               all_available,
                               ignore_packages):
        full_package_diff = {}
        logging.info("\n\nThis will diff a repoquery from all enabled yum\
                     repos, this is NOT comparing installed packages\n")
        column_list = ['Node', 'Package_Name',
                       'Control Package Version', 'Test Package Version']

        nodes = self.get_the_nodes(cache, control_url,
                                   test_url, all_available)
        even_nodes = self.check_for_even_nodes(nodes, column_list)
        if not even_nodes[0]:
            return [even_nodes[1], column_list]

        control_list = self.get_repoquery_logs(cache, control_url,
                                               nodes['control']['undercloud'])
        test_list = self.get_repoquery_logs(cache, test_url,
                                            nodes['test']['undercloud'])
        control_list = self.parse_list(control_list, ignore_packages)
        test_list = self.parse_list(test_list, ignore_packages)

        control_list = self.find_highest_version(control_list)
        test_list = self.find_highest_version(test_list)

        package_diff = self.diff_packages(control_list,
                                          test_list,
                                          not_found_message="not available")
        full_package_diff['repo_query'] = package_diff

        return [full_package_diff, column_list]

    def execute_compose_diff(self,
                             cache,
                             control_url,
                             test_url,
                             all_available,
                             ignore_packages):
        full_package_diff = {}
        logging.info(
            "\n\nThis will diff the rpms provided by the compose build.\n")
        column_list = ['Node', 'Package_Name',
                       'Control Package Version', 'Test Package Version']

        #    def get_compose_logs(self, cache, base_url):
        control_list = self.get_compose_logs(cache, control_url)
        test_list = self.get_compose_logs(cache, test_url)
        # parse_compose(self, json_result):
        control_list = self.parse_compose(control_list)
        test_list = self.parse_compose(test_list)
        control_list = self.parse_list(control_list, ignore_packages)
        test_list = self.parse_list(test_list, ignore_packages)

        control_list = self.find_highest_version(control_list)
        test_list = self.find_highest_version(test_list)

        package_diff = self.diff_packages(control_list,
                                          test_list,
                                          not_found_message="not available")
        full_package_diff['compose'] = package_diff

        return [full_package_diff, column_list]


@ click.command()
@ click.option("--control_url", "-c", required=True,
               help="a url that points to list of rpms that are used as the\
               control in the diff")
@ click.option("--test_url", "-t", required=True, help="a url that points to\
               the rpms to be compared against the control list")
@ click.option("--all_available", "-a", required=False, is_flag=True,
               default=False,
               help="Some jobs are not logging container rpms, use output from\
               repoquery instead")
@ click.option("--package_ignore", "-p", required=False,
               type=click.Path(exists=True),
               help="A file that enables some packages to be ignored from\
               the diff")
@ click.option("--diff_compose", "-q", required=False, is_flag=True,
               default=False,
               help="diff the metadata rpms.json from a compose")
@ click.option("--undercloud_only", "-u", required=False, is_flag=True,
               default=False, help="use the undercloud only, ignore the\
               controller, compute and ceph nodes")
@ click.option("--cpaas", "-p", required=False, default=False, is_flag=True,
               help="cpaas built rpms rev the release every stupid time\
               it builds, this option will ignore the release in compares")
def main(control_url,
         test_url,
         all_available,
         package_ignore,
         diff_compose,
         undercloud_only,
         cpaas):
    """
    This script takes two urls for ci log files and compares the rpms
    installed in each environment.  We have named the first a control_url as
    in a control and experiment to display the diff.

    The script will pull rpms from ALL the nodes available, and the containers
    hosted on that node. This workds with both upstream tripleo jobs and
    infrared job logs.

    USAGE:
        The script expects only the base url ( up to the logs dir ) of the
        logs from any job.
        e.g. https://logserver.rdoproject.org/foo/check/jobs/7822e6c/logs/

    """

    diff_builds = DiffBuilds()

    debug_format = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
    logging.basicConfig(level=logging.DEBUG,
                        format=debug_format,
                        datefmt='%m-%d %H:%M',
                        filename='debug.log',
                        filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter(': %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    sess = requests.session()
    cached_sess = CacheControl(sess)
    full_package_diff = {}
    # default ignore
    ignore_packages = {".*debuginfo",
                       ".*debugsource",
                       ".*-devel",
                       ".*-doc"}

    # debug inputs
    logging.debug("input: control_url: {}".format(control_url))
    logging.debug("input: test_url: {}".format(test_url))
    logging.debug("input: all_available: {}".format(all_available))
    logging.debug("input: package_ignore: {}".format(package_ignore))
    logging.debug("input: diff_compose: {}".format(diff_compose))
    logging.debug("input: undercloud_only: {}".format(undercloud_only))

    if package_ignore:
        with open(package_ignore) as f:
            ignore_packages.update(set(f.read().splitlines()))

    if not all_available and not diff_compose:
        results = diff_builds.execute_installed_package_diff(cached_sess,
                                                             control_url,
                                                             test_url,
                                                             all_available,
                                                             ignore_packages,
                                                             undercloud_only,
                                                             cpaas
                                                             )
        full_package_diff = results[0]
        column_list = results[1]

    elif all_available and not diff_compose:
        results = diff_builds.execute_repoquery_diff(cached_sess,
                                                     control_url,
                                                     test_url,
                                                     all_available,
                                                     ignore_packages
                                                     )
        full_package_diff = results[0]
        column_list = results[1]

    elif diff_compose:
        results = diff_builds.execute_compose_diff(cached_sess,
                                                   control_url,
                                                   test_url,
                                                   all_available,
                                                   ignore_packages
                                                   )
        full_package_diff = results[0]
        column_list = results[1]

    else:
        print("Error with options provided")

    logging.info("\n\n **** RESULT **** \n\n")
    logging.info("Control URL: {}".format(control_url))
    logging.info("Test URL: {}".format(test_url))
    for key in full_package_diff:
        if len(full_package_diff[key]) == 0:
            full_package_diff[key] = {'no_diff': [["No Diff Found",
                                                "No Diff Found"],
                                                ["No Diff Found",
                                                "No Diff Found"]]}
        diff_builds.display_packages_table(
            key, column_list, full_package_diff[key])


if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    main()
