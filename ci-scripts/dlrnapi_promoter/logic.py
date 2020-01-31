"""
This file contains classes and function for high level logic of the promoter
workflow
"""
import logging
import itertools

from dlrn_client import DlrnClient
from registries_client import RegistriesClient
from qcow_client import QcowClient
from common import PromotionError
from config import PromoterConfig


class Promoter(object):
    """
    This class embeds the promoter logic and its methods implement all the
    high level decisions around promotion
    """

    log = logging.getLogger('promoter')

    def __init__(self, config_file=None, overrides=None):
        self.config = PromoterConfig(config_file=config_file,
                                     overrides=overrides)
        # This message is also used by some test to understand if the
        # promoter is running the new or the legacy code by looking at the logs
        self.log.warning("This workflow is using the new modularized "
                         "code")
        self.dlrn_client = DlrnClient(self.config)
        self.registries_client = RegistriesClient(self.config)
        self.qcow_client = QcowClient(self.config)

    def select_candidates(self, candidate_label, target_label):
        """
        This method select candidates among the hashes that have been
        promoted to candidate label that can potentially be promoted to
        target label.
        Currently it's just a wrapper around the legacy get_latest_hashes
        function
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
            self.log.info("Candidate hashes younger than target label current"
                          ": {}".format(candidate_hashes_list))
        else:
            self.log.info("Candidate hashes: none found younger than target "
                          "label current")

        return candidate_hashes_list

    def promote(self, candidate_hash, candidate_label, target_label,
                allowed_clients=None):
        """
        This method drives the effective promotion of all the single component
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

        self.log.debug("Candidate hash '{}': clients allowed to promote: {}"
                       "".format(candidate_hash, allowed_clients))

        # FIXME: In python2 itertools.repeat needs a length parameter or it
        #  will just repeat self ad libitum. Python3 does not need it.
        for client in list(map(getattr,
                               itertools.repeat(self, len(allowed_clients)),
                               allowed_clients)):
            self.dlrn_client.check_named_hashes_unchanged()
            self.log.info("Candidate hash '{}': client {} attempting promotion"
                          "".format(candidate_hash, client))
            try:
                client.promote(candidate_hash, target_label,
                               candidate_label=candidate_label)
                promoted_pair = (candidate_hash, target_label)
            except PromotionError as e:
                self.log.error("Candidate hash '{}': Failed Promotion attempt")
                self.log.error(e)

        return promoted_pair

    def promote_label_to_label(self, candidate_label, target_label):
        """
        This method attempts the promotion of a series of hashes associated
        with a label to a target label
        This mathod replaces part of legacy promote_all_links
        :param candidate_label: the label whose associated hashes we'd like
        to promote
        :param target_label: the label to which a winning hash should be
        promoted
        :return: None
        """
        promoted_pair = ()
        selected_candidates = self.select_candidates(candidate_label,
                                                     target_label)
        if not selected_candidates:
            self.log.warning("Candidate label '{}': No candidate hashes"
                             "".format(candidate_label))
            return promoted_pair
        else:
            self.log.info("Candidate label '{}': {} candidates"
                          "".format(candidate_label, len(selected_candidates)))

        self.log.info("Candidate label '{}': Checking candidates that meet "
                      "promotion criteria for target label '{}'"
                      "".format(candidate_label, target_label))
        for candidate_hash in selected_candidates:
            required_jobs = self.config.promotion_criteria_map[target_label]
            self.log.debug("Candidate hash '{}': required jobs {}"
                           "".format(candidate_hash, required_jobs))
            successful_jobs = \
                set(self.dlrn_client.fetch_jobs(candidate_hash))
            if successful_jobs:
                self.log.info("Candidate hash '{}': successful jobs {}"
                              "".format(candidate_hash, successful_jobs))
            else:
                self.log.warning("Candidate hash '{}': NO successful jobs"
                                 "".format(candidate_hash))

            missing_jobs = list(required_jobs - successful_jobs)
            if missing_jobs:
                self.log.warning("Candidate hash '{}': missing jobs {}"
                                 "".format(candidate_hash, missing_jobs))
                self.log.warning("Candidate hash '{}': criteria NOT met "
                                 "for promotion to {}"
                                 "".format(candidate_hash, target_label))
                self.log.warning("Candidate hash '{}': {}"
                                 "".format(candidate_hash,
                                           self.dlrn_client.get_civotes_info()))
                continue

            self.log.info("Candidate hash '{}': criteria met, attempting "
                          "promotion to {}"
                          "".format(candidate_hash, target_label))
            promoted_pair = self.promote(candidate_hash,
                                         candidate_label,
                                         target_label)
            if promoted_pair:
                self.log.info("Candidate hash '{}': SUCCESSFUL promotion to {}"
                              "".format(candidate_hash, target_label))
                self.log.info("Candidate hash '{}': {}"
                              "".format(candidate_hash,
                                        self.dlrn_client.get_civotes_info(
                                            candidate_hash)))
                # stop here, don't try to promote other hashes
                break
            else:
                self.log.warning("Candidate hash '{}': FAILED promotion "
                                 "attempt to {}"
                                 "".format(candidate_hash, target_label))
                self.log.warning("Candidate hash '{}': {}"
                                 "".format(candidate_hash,
                                           self.dlrn_client.get_civotes_info(
                                               candidate_hash)))

        return promoted_pair

    def promote_all(self):
        """
        This method loops over all the labels specified in the config file
        and attempt to find and promote suitable candidates
        :return: a list of promoted (candidate, target) tuples
        """
        self.dlrn_client.fetch_current_named_hashes(store=True)

        promoted_pairs = []
        self.log.info("Starting promotion attempts for all labels")
        for target_label, candidate_label in \
                self.config.promotion_steps_map.items():
            self.log.info("Candidate label '{}': Attempting promotion to '{}'"
                          "".format(candidate_label, target_label))
            promoted_pair = self.promote_label_to_label(candidate_label,
                                                        target_label)
            if promoted_pair:
                promoted_pairs.append(promoted_pair)
            else:
                self.log.warning("Candidate label '{}': NO candidate "
                                 "hash promoted to {}"
                                 "".format(candidate_label, target_label))

        self.log.info("Summary: Promoted {} hashes this round"
                      "".format(len(promoted_pairs)))
        self.log.info("------- -------- Promoter terminated normally")
        return promoted_pairs
