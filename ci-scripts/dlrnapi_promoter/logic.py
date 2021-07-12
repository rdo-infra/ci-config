"""
This file contains classes and function for high level logic of the promoter
workflow
"""
import logging

from common import PromotionError
from dlrn_client import DlrnClient
from dockerfile_client import DockerfileClient
from qcow_client import QcowClient
from registries_client import RegistriesClient
from tabulate import tabulate


def print_job_table(log, c_hash_list, candidate_hash, promoted=False,
                    success_jobs=[], missing_jobs=[]):
    header1 = ['Aggregate Hash', 'Promoted', 'Description']
    header2 = {
        'Commit Hash': candidate_hash.commit_hash
        if hasattr(candidate_hash, 'commit_hash') else '',
        'Distro Hash': candidate_hash.distro_hash
        if hasattr(candidate_hash, 'distro_hash') else '',
        'Extended Hash': candidate_hash.extended_hash
        if hasattr(candidate_hash, 'extended_hash') else '',
        'Component': candidate_hash.component
        if hasattr(candidate_hash, 'component') else '',
        'Timestamp': str(candidate_hash.timestamp)
        if hasattr(candidate_hash, 'timestamp') else '',
        'Successful Jobs': "\n".join(list(success_jobs)),
        'Missing Jobs': "\n".join(list(missing_jobs))}
    if c_hash_list == []:
        c_hash_list.append(header1)
    c_hash_list.append([candidate_hash.aggregate_hash,
                        'Yes' if promoted else 'No',
                        tabulate([[i, j] for i, j in header2.items()],
                                 tablefmt='grid')])


def print_hash_table(log, hash_list):
    table_headers = ['Aggregate Hash', 'Commit Hash', 'Distro Hash',
                     'Extended Hash', 'Component', 'Timestamp']
    table_list = [table_headers]
    if isinstance(hash_list, list):
        for hashes in hash_list:
            table_list.append([
                hashes.aggregate_hash
                if hasattr(hashes, 'aggregate_hash') else '',
                hashes.commit_hash, hashes.distro_hash,
                hashes.extended_hash
                if hasattr(hashes, 'extended_hash') else '',
                hashes.component, hashes.timestamp])
    else:
        table_list.append([
            hash_list.aggregate_hash
            if hasattr(hash_list, 'aggregate_hash') else '',
            hash_list.commit_hash, hash_list.distro_hash,
            hash_list.extended_hash
            if hasattr(hash_list, 'extended_hash') else '',
            hash_list.component, hash_list.timestamp])
    log.info("\n {}".format(tabulate(table_list, headers='firstrow',
                                     tablefmt='grid')))


class Promoter(object):
    """
    This class embeds the promoter logic and its methods implement all the
    high level decisions around promotion
    """

    log = logging.getLogger('promoter')

    def __init__(self, config):
        """
        Instantiates a configuration object and all the clients for the
        promotion
        :param config_file: The path to the configuration file
        :param overrides: The command line overrides to the configuration
        """
        self.config = config
        self.dlrn_client = DlrnClient(self.config)
        self.registries_client = RegistriesClient(self.config)
        self.qcow_client = QcowClient(self.config)
        self.dockerfile_client = DockerfileClient(self.config)

    def select_candidates(self, candidate_label, target_label):
        """
        This method selects candidates among the hashes that have been
        promoted to candidate label and that can potentially be promoted to
        target label.
        :param candidate_label: The label identifying the pool of candidate
        hashes
        :param target_label:  The label to which the candidate would be promoted
        :return: A list of candidate hashes
        """
        candidate_hashes_list = self.dlrn_client.fetch_promotions(
            candidate_label, count=self.config.latest_hashes_count)

        if not candidate_hashes_list:
            self.log.warning("Candidate label '{}': No hashes fetched"
                             "".format(candidate_label))
            return candidate_hashes_list
        else:
            self.log.info("Candidate label '{}': Fetched {} hashes"
                          "".format(candidate_label,
                                    len(candidate_hashes_list)))

        # This will be a map of recent hashes candidate for
        # promotion. We'll map here the timestamp for each promotion to
        # promote name, if any
        candidate_hashes = {}
        for dlrn_hash in candidate_hashes_list:
            candidate_hashes[dlrn_hash.full_hash] = {}
            candidate_hashes[dlrn_hash.full_hash][candidate_label] = \
                dlrn_hash.timestamp

        old_hashes = self.dlrn_client.fetch_promotions(target_label)
        if not old_hashes:
            self.log.warning("Target label '{}': No hashes fetched."
                             " This could mean that the target label is new"
                             " or it's the wrong label"
                             "".format(target_label))
        else:
            self.log.info("Target label '{}': Fetched {} hashes"
                          "".format(target_label, len(old_hashes)))
            for dlrn_hash in old_hashes:
                # it may happen that an hash appears in this list,
                # but it's not from our list of candindates. If this happens
                # we're just ignoring it
                if dlrn_hash.full_hash in candidate_hashes:
                    candidate_hashes[dlrn_hash.full_hash][target_label] = \
                        dlrn_hash.timestamp

        # returning only the hashes younger than the latest promoted
        # this list is already in reverse time order
        for index, dlrn_hash in enumerate(candidate_hashes_list):
            if target_label in candidate_hashes[dlrn_hash.full_hash]:
                self.log.info("Target label '{}': current hash is {}"
                              "".format(target_label, dlrn_hash))
                candidate_hashes_list = candidate_hashes_list[:index]
                break

        if candidate_hashes_list:
            self.log.info("Candidate hashes younger than target label current")
            print_hash_table(self.log, candidate_hashes_list)
        else:
            self.log.info("Candidate hashes: none found younger than target "
                          "label current")

        return candidate_hashes_list

    def promote(self, candidate_hash, candidate_label, target_label,
                allowed_clients=None):
        """
        This method drives the effective promotion of all the parts that need
        promotion (dlrn, overcloud images, container images)
        :param candidate_hash: The candidate element to be promoted
        :param candidate_label: the label to which the element was previously
        promoted to
        :param target_label: The label to which promote the candidate
        :param allowed_clients: A list of client we are going to use for the
        promotion. The default is calling all the client, but when testing,
        we can decide to launch a single client or group of clients
        :return: None
        """
        promoted_pair = ()

        if self.config.dry_run:
            return

        if allowed_clients is None:
            allowed_clients = self.config.allowed_clients

        # DLRN client should always be called last,
        # This ensures the order of the called clients, it uses alphabetical
        # sorting, which is quite weak but works. If it becomes inconvenient,
        # we can just remove the loop here and act on clients singularly
        allowed_clients.sort(reverse=True)

        self.log.debug("Candidate hash '%s': clients allowed to promote: %s"
                       "", candidate_hash, ', '.join(allowed_clients))

        self.log.info("Candidate hash '%s': attempting promotion"
                      "", candidate_hash)
        candidate_hash.label = candidate_label
        for client_name in allowed_clients:
            client = getattr(self, client_name)
            self.dlrn_client.check_named_hashes_unchanged()
            try:
                client.promote(candidate_hash, target_label,
                               candidate_label=candidate_label)
                self.log.debug(
                    "Candidate hash '%s': client %s SUCCESSFUL promotion"
                    "", candidate_hash, client_name)
            except PromotionError as e:
                self.log.error("Candidate hash '%s': client %s FAILED "
                               "promotion attempt to %s"
                               "", candidate_hash, client_name, target_label)
                self.log.exception(e)
                raise

        promoted_pair = (candidate_hash, target_label)
        self.log.info("Candidate hash '%s': SUCCESSFUL promotion to %s"
                      "", candidate_hash, target_label)
        return promoted_pair

    def promote_label_to_label(self, candidate_label, target_label):
        """
        Launch the selection of candidate hashes in a certain label, verifies
        that it meets the criteria for promotion, and then launches the
        single hash promotion
        :param candidate_label: the label whose associated hashes we'd like
        to promote
        :param target_label: the label to which a winning hash should be
        promoted
        :return: None
        """
        promoted_pair = ()
        jobs_list = []
        selected_candidates = self.select_candidates(candidate_label,
                                                     target_label)
        if not selected_candidates:
            self.log.warning("Candidate label '%s': No candidate hashes"
                             "", candidate_label)
            return promoted_pair
        else:
            self.log.info("Candidate label '%s': %d candidates"
                          "", candidate_label, len(selected_candidates))

        self.log.info("Candidate label '%s': Checking candidates that meet "
                      "promotion criteria for target label '%s'"
                      "", candidate_label, target_label)
        required_jobs = self.config.promotions[target_label]['criteria']
        for candidate_hash in selected_candidates:
            ci_votes = self.dlrn_client.get_civotes_info(candidate_hash)
            successful_jobs = \
                set(self.dlrn_client.fetch_jobs(candidate_hash))
            if successful_jobs:
                self.log.info("Candidate hash '%s': vote details page "
                              "- %s", candidate_hash,
                              ci_votes)
            else:
                self.log.warning("Candidate hash '%s': NO successful jobs"
                                 "", candidate_hash)

            missing_jobs = set(required_jobs - successful_jobs)
            print_job_table(self.log, jobs_list, candidate_hash, False,
                            successful_jobs, missing_jobs)
            if missing_jobs:
                # self.log.warning("Candidate hash '%s': missing jobs %s"
                #                 "", candidate_hash, missing_jobs)
                self.log.warning("Candidate hash '%s': criteria NOT met "
                                 "for promotion to %s"
                                 "", candidate_hash, target_label)
                continue

            self.log.info("Candidate hash '%s': criteria met, attempting "
                          "promotion to %s"
                          "", candidate_hash, target_label)
            promoted_pair = self.promote(candidate_hash,
                                         candidate_label,
                                         target_label)
            if promoted_pair:
                # stop here, don't try to promote other hashes
                print_job_table(self.log, jobs_list, candidate_hash, True,
                                successful_jobs, missing_jobs)
                break
        self.log.info("\n {}".format(tabulate(jobs_list,
                                              headers='firstrow',
                                              tablefmt='grid')))
        return promoted_pair

    def promote_all(self):
        """
        This method loops over all the combination of labels specified in the
        config file (eg. from tripleo-ci-testing to current-tripleo)
        :return: a list of promoted (candidate, target) tuples
        """
        self.dlrn_client.fetch_current_named_hashes(store=True)
        promoted_pairs = []
        self.log.info("Starting promotion attempts for all labels")

        for target_label, target_criteria in \
                self.config.promotions.items():
            candidate_label = target_criteria['candidate_label']
            self.log.info("Candidate label '%s': Attempting promotion to '%s'"
                          "", candidate_label, target_label)
            promoted_pair = None
            try:
                promoted_pair = self.promote_label_to_label(candidate_label,
                                                            target_label)
            except PromotionError:
                self.log.error("Error while trying to promote %s to %s",
                               candidate_label, target_label)
            if promoted_pair:
                promoted_pairs.append(promoted_pair)
            else:
                self.log.warning("Candidate label '%s': NO candidate "
                                 "hash promoted to %s"
                                 "", candidate_label, target_label)
        self.log.info("Summary: Promoted {} hashes this round"
                      "".format(len(promoted_pairs)))
        self.log.info("------- -------- Promoter terminated normally")
        return promoted_pairs
