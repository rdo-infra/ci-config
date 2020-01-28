"""
This file contains classes and function for high level logic of the promoter
workflow
"""
import logging

from dlrn_interface import DlrnClient, DlrnHash
from registry import RegistryClient
from qcow import QcowClient
from legacy_promoter import check_named_hashes_unchanged, get_latest_hashes


class PromotionError(Exception):
    pass


class PromoterLogic(object):
    """
    This class embeds the promoter logic and its methods implement all the
    high level decisions around promotion
    """

    log = logging.getLogger('promoter')

    def __init__(self, config):
        self.config = config
        self.dlrn_client = DlrnClient(self.config)
        self.registry_client = RegistryClient(self.config)
        self.qcow_client = QcowClient(self.config)

    def check_named_hashes_unchanged(self):
        """
        This function wraps a legacy function to pass config parameters
        :return: None
        """
        check_named_hashes_unchanged(self.config.release,
                                     self.config.promotion_steps_map,
                                     self.dlrn_client.api_instance)

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
        if self.config.pipeline_type == "single":
            # get_latest_hashes is imported from legacy code
            return get_latest_hashes(self.dlrn_client.api_instance,
                                     target_label, candidate_label,
                                     self.config.latest_hashes_count)
        elif self.config.pipeline_type == "component":
            self.log.error("Candidate selection for aggregate hashes is not "
                           "implemented yet")

    def promote(self, candidate, target_label):
        """
        This method drives the effective promotion of all the single component
        :param candidate: The candidate element to be promoted
        :param target_label: The label to which promote the candidate
        :return: None
        """
        # replaces promote_all_links - noop promotion
        if self.config.dry_run:
            return

        # replaces promote_all_links -effective promotion
        # replaces promote_all_links - containers promotion
        self.check_named_hashes_unchanged()
        if self.config.allow_containers_promotion:
            self.registry_client.promote_containers(candidate, target_label)
        # replaces promote_all_links - qcow promotion
        self.check_named_hashes_unchanged()
        if self.config.allow_qcows_promotion:
            self.qcow_client.promote_images(candidate, target_label)
        # replaces promote_all_links - dlrn promotion
        self.check_named_hashes_unchanged()
        if self.config.allow_dlrn_promotion:
            self.dlrn_client.promote_hash(candidate, target_label)

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
        # replaces promote_all_links - candidate hashes selection
        for selected_candidate in self.select_candidates(candidate_label,
                                                         target_label):
            self.log.info('Checking hash %s from %s for promotion criteria',
                          selected_candidate, candidate_label)
            # convert hash. new fetch_jobs function works with DlrnHash
            selected_candidate = DlrnHash(from_dict=selected_candidate)
            successful_jobs = set(self.dlrn_client.fetch_jobs(
                selected_candidate))
            # convert back hash, the promote_* functions still work
            # with legacy hashes
            selected_candidate = selected_candidate.dump_to_dict()
            required_jobs = self.config.promotion_criteria_map[target_label]
            # The label reject condition is moved as config time check
            # replaces promote_all_links - hashes reject condition
            missing_jobs = list(required_jobs - successful_jobs)
            if not missing_jobs:
                try:
                    self.promote(selected_candidate, target_label)
                    self.log.info('SUCCESS promoting %s-%s %s as %s (%s)',
                                  self.config.distro, self.config.release,
                                  candidate_label, target_label,
                                  selected_candidate)
                    self.log.info(
                        '%s \n%s/api/civotes_detail.html?\
                        commit_hash=%s&distro_hash=%s'.replace(" ", ""),
                        'DETAILED SUCCESSFUL STATUS: ',
                        self.config.api_url,
                        selected_candidate['commit_hash'],
                        selected_candidate['distro_hash'])
                    # stop here, don't try to promote other hashes
                    break
                except Exception:
                    # replaces promot_all_links - effective promotion failure
                    self.log.info('FAILED promoting %s-%s %s as %s (%s)',
                                  self.config.distro, self.config.release,
                                  candidate_label, target_label,
                                  selected_candidate)
                    civotes_info = self.dlrn_client.get_civotes_info(
                        selected_candidate)
                    self.log.info(civotes_info)
                    raise
            else:
                self.log.info(
                    'Skipping promotion of %s-%s %s from %s to %s, missing '
                    'successful jobs: %s',
                    self.config.distro, self.config.release,
                    candidate_label, target_label, missing_jobs)
                self.log.info('Check Results at:')
                self.log.info(
                    '%s \n%s/api/civotes_detail.html?'
                    'commit_hash=%s&distro_hash=%s'.replace(" ", ""),
                    'DETAILED MISSING JOBS: ',
                    self.config.api_url,
                    selected_candidate['commit_hash'],
                    selected_candidate['distro_hash'])

        self.log.info("No more candidates")

    def promote_all_links(self):
        """
        This method loops over all the labels specified in the config file
        and attempt to find and promote suitable candidates
        This method replaces part of the legacy promote_all_links function
        :return: None
        """
        # replaces promote_all_links - labels loop
        for target_label, candidate_label in \
                self.config.promotion_steps_map.items():
            self.promote_label_to_label(candidate_label, target_label)
