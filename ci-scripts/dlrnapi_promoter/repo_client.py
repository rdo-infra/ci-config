import csv
import logging
import os

import yaml
from common import get_release_map

try:
    # Python3 imports
    from io import StringIO as csv_io  # noqa N813
    from urllib import request as url
except ImportError:
    # Python 2 imports
    import urllib2 as url
    from StringIO import StringIO as csv_io  # noqa N813


class RepoError(Exception):
    pass


class RepoClient(object):

    log = logging.getLogger("promoter")

    def __init__(self, config):
        self.config = config
        self.root_url = self.config.repo_url
        self.containers_list_base_url = \
            config.containers['containers_list_base_url']
        self.containers_list_path = config.containers['containers_list_path']
        self.release = config.release
        self.containers_list_exclude_config = \
            config.containers["containers_list_exclude_config"]
        self.build_method = config.containers["build_method"]
        self.container_preffix = config.containers["container_preffix"]

    def get_versions_csv(self, dlrn_hash, candidate_label):
        """
        Download a versions.csv file relative to a commit referenced by
        hash. Aggregate Hash also require the label to be specified
        :param dlrn_hash: The hash associated to the label
        :param candidate_label:
        :return: A csv reader (None in case of error)
        """

        versions_url = ("{}/{}/versions.csv"
                        "".format(self.root_url, dlrn_hash.commit_dir))
        self.log.debug("Accessing versions at %s", versions_url)
        try:
            versions_content = url.urlopen(versions_url).read()
        except url.URLError as ex:
            self.log.error("Error downloading versions.csv file at %s",
                           versions_url)
            self.log.exception(ex)
            return None

        # csv.DictReader takes a file as argument, not a string. The only
        # file I have from urlopen is an undecoded file, that in python3 is a
        # byte string. The only way to offer a file to csv is to read,
        # eventually convert and use a stringIO

        if not isinstance(versions_content, str):
            versions_content = versions_content.decode("UTF-8")

        csv_file = csv_io(versions_content)
        versions_reader = csv.DictReader(csv_file)
        return versions_reader

    def get_commit_sha(self, versions_csv_reader, project_name):
        """
        extract a commit sha for the specified project from a versions.csv file
        :param versions_csv_reader: A csv reader for the versions.csv file
        :param project_name: The name of the project to look for
        :return: A sha1 from a commit (None if not found
        """

        commit_sha = None
        self.log.debug("Looking for sha commit of project %s in %s",
                       project_name,
                       versions_csv_reader)
        for row in versions_csv_reader:
            if row and row['Project'] == project_name:
                commit_sha = row['Source Sha']
                break

        if commit_sha is None:
            self.log.error("Unable to find commit sha for project %s",
                           project_name)

        return commit_sha

    def get_containers_list(self, tripleo_common_commit, load_excludes=True):
        """
        Gets a tripleo containers template file from a specific
        tripleo-common commit
        :param tripleo_common_commit:  A sha1 from a tripleo-common commit
        :return: A dict of containers base names
        """

        containers_url = os.path.join(self.containers_list_base_url,
                                      tripleo_common_commit,
                                      self.containers_list_path)

        self.log.debug("Attempting Download of containers template at %s",
                       containers_url)
        try:
            # Download and read the container file(overcloud_containers.yaml
            # or tripleo_containers.yaml) file
            # in bytes format from tripleo-common
            containers_content = url.urlopen(containers_url).read()
        except url.URLError as ex:
            self.log.error("Unable to download containers template at %s",
                           containers_url)
            self.log.exception(ex)
            return {'containers_list': []}

        # convert it readable content from byte to string
        if not isinstance(containers_content, str):
            containers_content = containers_content.decode()

        # Load the yaml content for further parsing
        container_list = yaml.safe_load(containers_content)

        # container_preffix is loaded from config
        # In container-images/tripleo_containers.yaml, the containers
        # are named openstack-* for master/victoria onwards.
        # In container-images/overcloud_containers.yaml, the containers
        # are named distro-binary-* for older branches.

        if container_list:
            if 'container_images' in container_list:

                # The parsed yaml file contains the following data structure
                # in overcloud_containers.yaml:
                # for queens
                # container_images:
                # - imagename: docker.io/tripleo/centos-binary-aodh-api:current
                # container_images:
                # - imagename: docker.io/tripleo/centos-binary-aodh-api:current
                #   image_source: kolla
                # in tripleo_containers.yaml:
                # container_images:
                # - image_source: tripleo
                #   imagename: quay.io/tripleo/openstack-base:current-tripleo

                if self.release in ["queens", "stein",
                                    "train", "ussuri", "osp16-2"]:
                    if self.container_preffix != "centos-binary-":
                        self.container_preffix = "centos-binary-"
                    full_list = [
                        i['imagename'].rpartition('/')[-1].split(':')[0]
                        for i in container_list['container_images']
                    ]
                else:
                    full_list = [
                        i['imagename'].rpartition('/')[-1].split(':')[0]
                        for i in container_list['container_images']
                        if i['image_source'] in ['tripleo', 'kolla']
                    ]

                # filter imagename based on image_source
                # for imagename and release up to ussuri
                # docker.io/tripleomaster/centos-binary-aodh-api:current-tripleo
                # We need to get aodh-api as a container name by striping with
                # '/' and spliting -binary from the imagename
                #
                # for imagename and release: master/victoria onwards
                # quay.io/tripleomaster/openstack-base:current-tripleo
                # we need to get tempest as a container name by striping with
                # '/' and splitting -openstack from the imagename

                full_list = [
                    i.split(self.container_preffix)[-1]
                    for i in full_list
                    if self.container_preffix in i
                ]
        else:
            full_list = []
            self.log.error("No containers name found in %s", containers_url)

        if load_excludes:
            containers_dict = self.load_excludes(full_list)
            return containers_dict
        containers_dict = {'containers_list': full_list}
        return containers_dict

    def load_excludes(self, full_list):
        """
        Filter the list using and exclude list from an exxternal source
        Tries to download the source from a url and find the correct list for
        the release. The exclusion is completely optional, so if any error is
        encountered, a message is logged then the original list is returned
        :param full_list: the initial full list of containers
        :return: a list of containers optionally excluding some.
        """
        exclude_content_yaml = None
        exclude_content = None
        exclude_list = []
        ppc_exclude_list = []
        try:
            exclude_content_yaml = url.urlopen(
                self.containers_list_exclude_config).read().decode()
        except (url.URLError, ValueError) as ex:
            self.log.warning("Unable to download containers exclude config at "
                             "%s, no exclusion",
                             self.containers_list_exclude_config)
            self.log.exception(ex)

        if exclude_content_yaml:
            try:
                exclude_content = yaml.safe_load(exclude_content_yaml)
            except yaml.YAMLError:
                self.log.error("Unable to read container exclude config_file")

        # Check for downstream release and set appropriate release for the
        # same, for osp16-2 -> rhos-16.2 and osp-17 -> rhos-17
        self.release = get_release_map(self.release)

        if exclude_content:
            try:
                exclude_list = exclude_content['exclude_containers'][
                    self.release]
            except KeyError:
                self.log.warning("Unable to find container exclude list for "
                                 "%s", self.release)

            try:
                ppc_exclude_list = exclude_content['exclude_ppc_containers'][
                    self.release]
            except KeyError:
                self.log.warning("Unable to find ppc container exclude list "
                                 "for %s", self.release)

        containers_full_list = full_list.copy()
        for name in exclude_list:
            try:
                containers_full_list.remove(name)
                self.log.info("Excluding %s from the containers list", name)
            except ValueError:
                self.log.debug("%s not in containers list", name)

        containers_dict = {'containers_list': containers_full_list}
        if ppc_exclude_list:
            ppc_containers_list = full_list.copy()
            for name in ppc_exclude_list:
                try:
                    ppc_containers_list.remove(name)
                    self.log.info("Excluding %s from the ppc containers list",
                                  name)
                except ValueError:
                    self.log.debug("%s not in containers list", name)
            containers_dict['ppc_containers_list'] = ppc_containers_list

        return containers_dict
