import csv
import logging
import re
import os

try:
    # Python3 imports
    import urllib.request as url
except ImportError:
    # Python 2 imports
    import urllib2 as url


class RepoError(Exception):
    pass


class RepoClient(object):

    log = logging.getLogger("promoter")

    def __init__(self, config):
        self.config = config
        self.root_url = self.config.repo_url
        self.containers_list_base_url = config.containers_list_base_url
        self.containers_list_path = config.containers_list_path

    def get_versions_csv(self, dlrn_hash, candidate_label):
        """
        Download a versions.csv file relative to a commit referenced by
        hash. Aggregate Hash also require the label to be specified
        :param dlrn_hash: The hash associated to the label
        :param candidate_label:
        :return:
        """
        dlrn_hash.label = candidate_label
        versions_url = ("{}/{}/versions.csv"
                        "".format(self.root_url,
                                  dlrn_hash.commit_dir))
        self.log.info("Accessing versions at %s", versions_url)
        try:
            versions_file = url.urlopen(versions_url)
        except url.URLError as ex:
            self.log.exception(ex)
            return None

        versions_reader = csv.DictReader(versions_file)
        print(versions_reader.next())
        return versions_reader

    def get_commit_sha(self, versions_csv_reader, project_name):
        """
        extract a commit sha for the specified project from a versions.csv file
        :param versions_csv_reader: A csv reader for the versions.csv file
        :param project_name: The name of the project to look for
        :return: A sha1 from a commit (None if not found
        """

        commit_sha = None
        for row in versions_csv_reader:
            if row and row['Project'] == project_name:
                commit_sha = row['Source Sha']
                break

        if commit_sha is None:
            self.log.warning("unable to find commit sha for project %s",
                             project_name)

        return commit_sha

    # TODO(gcerami) Improve logging
    def get_containers_list(self, tripleo_common_commit):
        """
        Gets a tripleo containers template file from a specific
        tripleo-common commit
        :param candidate_hash:
        :param candidate_label:
        :return: A list of containers base names
        """

        print("contaienrs_list_path", self.containers_list_path)
        print("contaienrs_list_base_url", self.containers_list_base_url)
        print("tripleo commit", tripleo_common_commit)

        containers_url = os.path.join(self.containers_list_base_url,
                                      tripleo_common_commit,
                                      self.containers_list_path)

        try:
            containers_content = url.urlopen(containers_url).read()
        except url.URLError as ex:
            self.log.exception(ex)
            return []

        full_list = re.findall("(?<=name_prefix}}).*(?={{name_suffix)",
                               containers_content)

        return full_list
