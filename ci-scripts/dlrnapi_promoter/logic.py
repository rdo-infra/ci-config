"""
This file contains classes and function for high level logic of the promoter
workflow
"""
import logging

from dlrn_interface import DlrnClient
from registry import RegistryClient
from qcow import QcowClient


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
        candidate_hashes_list = self.dlrn_client.fetch_hashes(
            candidate_label, count=self.config.latest_hashes_count,
            sort="timestamp", reverse=True)

        if candidate_hashes_list is None:
            self.log.error(
                'Failed to fetch any hashes for %s, skipping promotion',
                candidate_label)
            return []

        # This will be a map of recent hashes candidate for
        # promotion. We'll map
        # here the timestamp for each promotion to promote name, if any
        candidate_hashes = {}
        for hash in candidate_hashes_list:
            candidate_hashes[hash.full_hash] = {}
            candidate_hashes[hash.full_hash][candidate_label] = hash.timestamp

        old_hashes = self.dlrn_client.fetch_hashes(target_label)
        if old_hashes is None:
            self.log.warning('Failed to fetch hashes for %s, no previous '
                             'promotion or typo in the link name',
                             target_label)
        else:
            for hash in old_hashes:
                # it may happen that an hash appears in this list,
                # but it's not from
                # our list of candindates. If this happens we're just
                # ignoring it
                if hash.full_hash in candidate_hashes:
                    candidate_hashes[hash.full_hash][target_label] = \
                        hash.timestamp

        # returning only the hashes younger than the latest promoted
        # this list is already in reverse time order
        for index, hash in enumerate(candidate_hashes_list):
            if target_label in candidate_hashes[hash.full_hash]:
                self.log.info(
                    'Current "%s" hash is %s' % (target_label, hash))
                candidate_hashes_list = candidate_hashes_list[:index]
                break

        if candidate_hashes_list:
            self.log.debug(
                'Remaining hashes after removing ones older than the '
                'currently promoted: %s', candidate_hashes_list)
        else:
            self.log.debug(
                'No remaining hashes after removing ones older than the '
                'currently promoted')

        return candidate_hashes_list

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
        self.dlrn_client.check_named_hashes_unchanged()
        if self.config.allow_containers_promotion:
            self.registry_client.promote_containers(candidate,
                                                    target_label)
        # replaces promote_all_links - qcow promotion
        self.dlrn_client.check_named_hashes_unchanged()
        if self.config.allow_qcows_promotion:
            self.qcow_client.promote_images(candidate, target_label)
        # replaces promote_all_links - dlrn promotion
        self.dlrn_client.check_named_hashes_unchanged()
        if self.config.allow_dlrn_promotion:
            self.dlrn_client.promote_hash(candidate, target_label)

        self.dlrn_client.update_current_named_hashes(candidate, target_label)

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
            successful_jobs = set(self.dlrn_client.fetch_jobs(
                selected_candidate))
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
                        selected_candidate.commit_hash,
                        selected_candidate.distro_hash)
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
                    selected_candidate.commit_hash,
                    selected_candidate.distro_hash)

        self.log.info("No more candidates")

    def promote_all_links(self):
        """
        This method loops over all the labels specified in the config file
        and attempt to find and promote suitable candidates
        This method replaces part of the legacy promote_all_links function
        :return: None
        """
        # replaces promote_all_links - labels loop
        self.dlrn_client.fetch_current_named_hashes(store=True)

        for target_label, candidate_label in \
                self.config.promotion_steps_map.items():
            self.promote_label_to_label(candidate_label, target_label)
