"""
This file contains classes and methods to interact with dlrn server
dlrn configuration options, dlrn repos
"""
import contextlib
import copy
import datetime
import dlrnapi_client
import logging
import os
import json
import yaml
import tempfile

from dlrn_hash import DlrnCommitDistroHash, DlrnAggregateHash, DlrnHash

try:
    import urllib2 as url
except ImportError:
    import urllib.request as url
try:
    import ConfigParser as ini_parser
except ImportError:
    import configparser as ini_parser

try:
    # Python3 import
    import StringIO as sio
except ImportError:
    # Python2 import
    import io as sio
try:
    # Python3 import
    from json.decoder import JSONDecodeError
except ImportError:
    # Python 2
    JSONDecodeError = ValueError

from common import PromotionError
from dlrnapi_client.rest import ApiException


class HashChangedError(Exception):
    """
    Raised when hashes change during a promotion
    """
    pass


class DlrnClientConfig(object):
    """
    Config class for direct calls to DlrnClient
    without a full config (e.g. from the staging environment)
    """

    def __init__(self, **kwargs):
        args = ['dlrnauth_username', 'dlrnauth_password', 'api_url']
        for arg in args:
            try:
                setattr(self, arg, kwargs[arg])
            except KeyError:
                pass


class DlrnClient(object):
    """
    This class represent a wrapper around dlrnapi client operations to perform
    complex operations on hashes
    """

    log = logging.getLogger("promoter")

    def __init__(self, config):
        """
        like all the the other inits around this code, the init will gather
        relevant information for this class and put them into local shortcuts
        :param config: The global promoter config or the reduced dlrnclient
        config
        """
        self.config = config
        # TODO(gcerami): fix credentials gathering
        dlrnapi_client.configuration.password = self.config.dlrnauth_password
        dlrnapi_client.configuration.username = self.config.dlrnauth_username
        api_client = dlrnapi_client.ApiClient(host=self.config.api_url)
        self.api_instance = dlrnapi_client.DefaultApi(api_client=api_client)
        self.last_promotions = {}

        # Variable to detect changes on the hash while we are running a
        # promotion
        self.named_hashes_map = {}

        # This way of preparing parameters and configuration is copied
        # directly from dlrnapi CLI and ansible module
        self.hashes_params = dlrnapi_client.PromotionQuery()
        self.jobs_params = dlrnapi_client.Params2()
        self.jobs_params_aggregate = dlrnapi_client.Params3()
        self.report_params = dlrnapi_client.Params3()
        self.promote_params = dlrnapi_client.Promotion()
        self.log.debug("Promoter DLRN client: API URL: {}, user: {}"
                       "".format(api_client.host,
                                 self.config.dlrnauth_username))

    def update_current_named_hashes(self, dlrn_hash, label):
        self.log.debug("Check named hashes: Updating stored value of named "
                       "hash for {} to {}"
                       "".format(label, dlrn_hash))
        self.named_hashes_map.update({label: dlrn_hash})

    def fetch_current_named_hashes(self, store=False):
        """
        Get latest known named hashes from dlrn. The latest know will be
        checked regularly during promotion run to bail out in case of any
        outside interference that could alter the local state
        :param store: If true, the local named_hash_map will be modified too
        :return: A dictionary with name to hash {'current-tripleo': 'xyz',
        """
        named_hashes = {}
        for promote_name in self.config.promotion_steps_map.keys():
            latest_named = self.fetch_promotions(promote_name, count=1)
            update = {promote_name: latest_named}
            named_hashes.update(update)
            self.log.debug("Check named hashes: Updating value of named"
                           " hash for {} to {}"
                           "".format(promote_name, latest_named.full_hash))
            if store:
                self.named_hashes_map.update(update)
                self.log.debug("Check named hashes: updated permanent map")

        return named_hashes

    def check_named_hashes_unchanged(self):
        """
        Fetch latest named hashes and compare to the initial named_hashes_map
        If they are different log error and raise Exception
        :param label: The label to check for changes
        :return: None
        """
        latest_named_hashes = self.fetch_current_named_hashes()
        for label, stored_dlrn_hash in self.named_hashes_map.items():
            try:
                fetched_dlrn_hash = latest_named_hashes[label]
            except KeyError:
                # We don't have the label in the new hash it was created
                # recently adn we don't have anything to compare it to
                # We only care about hashes we knew and have changed.
                continue
            if fetched_dlrn_hash != stored_dlrn_hash:
                self.log.error("Check named hashes: named hashes for label "
                               "'{}' changed since last check. At promotion "
                               "start: {}. Now: {}"
                               "".format(label, stored_dlrn_hash,
                                         fetched_dlrn_hash))
                raise HashChangedError("Named Hashes Changed since promotion "
                                       "start, aborting.")

    def fetch_jobs(self, dlrn_hash):
        """
        This method fetch a list of successful jobs from a dlrn server for a
        specific hash identifier.
        :param dlrn_id: The dlrn identifier to fetch jobs from. It could be
        either a DlrnHash or a DlrnAggregateHash
        :return: A list of job ids (str)
        """

        api_call = None
        jobs_params = None
        hash_type = type(dlrn_hash)

        if hash_type is DlrnCommitDistroHash:
            api_call = self.api_instance.api_repo_status_get
            jobs_params = self.jobs_params
        elif hash_type is DlrnAggregateHash:
            api_call = self.api_instance.api_agg_status_get
            jobs_params = self.jobs_params_aggregate
        else:
            raise TypeError("Unrecognized dlrn_hash type: {}".format(hash_type))

        params = copy.deepcopy(jobs_params)
        dlrn_hash.dump_to_params(params)
        params.success = str(True)

        try:
            self.log.debug("Hash '{}': fetching list of successful "
                           "jobs".format(dlrn_hash))
            jobs = api_call(params)
        except ApiException as ae:
            message = ae.body
            try:
                body = json.loads(ae.body)
                message = body['message']
            except JSONDecodeError:
                pass
            self.log.error("Exception while fetching jobs from API endpoint "
                           "({}) {}: {}"
                           "".format(ae.status, ae.reason, message))
            self.log.error("------- -------- Promoter aborted")
            raise

        if jobs:
            self.log.debug("Fetched {} successful jobs for hash {}"
                           "".format(len(jobs), dlrn_hash))
            for job in jobs:
                self.log.debug("{} passed on {}, logs at '{}'"
                               "".format(job.job_id,
                                         datetime.datetime.fromtimestamp(
                                             job.timestamp).isoformat(),
                                         job.url))
        else:
            self.log.debug("No successful jobs for hash {}"
                           "".format(dlrn_hash))

        return [details.job_id for details in jobs]

    def hashes_to_hashes(self, api_hashes, remove_duplicates=False):
        """
        Converts a list of hashes provided as response from api to a list
        of DlrnHash or DlrnAggregateHash objects
        :param api_hashes: The list of hashes to convert
        :param remove_duplicates: If true all the duplicate elements in the
        list will be removed
        :return: a list of DlrnHash or DlrnAggregateHash objects
        """
        result = []
        for hashes in api_hashes:
            hash_obj = DlrnHash(source=hashes)
            # we could use a set, but then we'd lose the order
            if remove_duplicates and hash_obj in result:
                continue
            self.log.debug("Added hash {} built from {}"
                           "".format(hash_obj, hashes))
            result.append(hash_obj)

        return result

    def fetch_promotions_from_hash(self, dlrn_hash, count=None):
        """
        Wrapper around fetch_hashes to fetch hashes from a promotion dlrn_hash
        :param dlrn_hash:  The dlrn_hash that contains commit and distro
        criterias for fetching
        :param count: The max amount of hashes to return
        :return:
        """
        params = copy.deepcopy(self.hashes_params)
        dlrn_hash.dump_to_params(params)
        self.log.debug("Fetching promotion hashes from hash {}"
                       "".format(dlrn_hash))
        hash_list = self.fetch_hashes(params, count=count)
        return hash_list

    def fetch_promotions(self, label, count=None):
        """
        Wrapper around fetch_hashes to fetch hashes from a promotion label
        :param label: the label to use as criteria for fetching
        :param count: the max amount of hashes to return
        :return:
        """
        params = copy.deepcopy(self.hashes_params)
        params.promote_name = label
        self.log.debug("Fetching promotion hashes from label {}"
                       "".format(label))
        hash_list = self.fetch_hashes(params, count=count)
        return hash_list

    def fetch_hashes(self, params, count=None, sort=None, reverse=None):
        """
        This is wrapper around dlrnapi client call to promotions.
        If fetches hashes from the promotion api following criteria,
        and eventually sorts the results.
        :param params: the dlrnapi params to use as criteria for fetching
        :param count: the max amount of hashes to return
        :param sort: Defines the method for sorting the results. The default
        from the api is to sort by reverse timestamp.
        :param reverse: bool value to define if we want to invert sorting method
        :return: A single hash when count=1. A list of hashes otherwise
        """
        if count is not None:
            params.limit = int(count)

        self.log.debug("Fetching hashes with criteria: {}"
                       "".format(params))
        try:
            # API documentation says the hashes are returned in reverse
            # timestamp order (from newest to oldest) by defaut
            api_hashes = self.api_instance.api_promotions_get(params)
            hash_list = self.hashes_to_hashes(api_hashes,
                                              remove_duplicates=True)
        except ApiException as ae:
            message = ae.body
            try:
                body = json.loads(ae.body)
                message = body['message']
            except JSONDecodeError:
                pass
            self.log.error("Exception while fetching promotions from API "
                           "endpoint: ({}) {}: {}"
                           "".format(ae.status, ae.reason, message))
            self.log.error("------- -------- Promoter aborted")
            raise

        if sort == "timestamp" and reverse is not None:
            hash_list.sort(key=lambda hashes: hashes.timestamp, reverse=reverse)

        if not hash_list:
            self.log.debug("No hashes fetched")
        else:
            self.log.debug("Fetch Hashes: fetched {} hashes: {}"
                           "".format(len(hash_list), hash_list))

        if count == 1 and len(hash_list) != 0:
            return hash_list[0]

        # if count is None, list[:None] will return the whole list
        return hash_list

    def promote(self, dlrn_hash, target_label, candidate_label=None,
                create_previous=True):
        """
        This method prepares the promotion environment for the hash.
        It creates a previous promotion link if it's requested. and orchestrate
        the calls to the actual promotion function
        :param dlrn_hash: The hash to promoted
        :param target_label: The name to promote the hash to
        :param candidate_label: The name the hash was recently promoted to,
        if any
        :param create_previous: A bool value to define if we want to also
        create a previous link for the previous hash value of target_label
        :return: None
        """
        if create_previous:
            incumbent_hash = self.fetch_promotions(target_label, count=1)
            # Save current hash as previous-$link
            if incumbent_hash is not None:
                previous_target_label = "previous-" + target_label
                self.log.info("Dlrn promote '{}' from {} to {}: moving "
                              "previous promoted hash '{}' to {}"
                              "".format(dlrn_hash, candidate_label,
                                        target_label, incumbent_hash,
                                        previous_target_label))
                self._promote_hash(incumbent_hash, previous_target_label,
                                   candidate_label=target_label)
            else:
                self.log.warning("Dlrn promote '{}' from {} to {}: No previous "
                                 "promotion found"
                                 "".format(dlrn_hash, candidate_label,
                                           target_label))

        self.log.info("Dlrn promote '{}' from {} to {}: Attempting promotion"
                      "".format(dlrn_hash, candidate_label, target_label))
        self._promote_hash(dlrn_hash, target_label,
                           candidate_label=candidate_label)

    def _promote_hash(self, dlrn_hash, target_label, candidate_label=None):
        """

        This method promotes an hash identifier to a target label
        from another POV the hash is labeled as the target
        from another yet POV the label becomes a link to the hash identifier
        :param dlrn_hash: The dlrn hash to promote
        :param target_label: The label/name to promote dlrn_hash to
        :param candidate_label: The name/label the dlrn_hash was recently
        promoted to, if any (mandatory for aggregate promotion)
        :return: None
        """
        hash_type = type(dlrn_hash)
        self.log.debug("Dlrn promote '{}' from {} to {}: promoting a {}"
                       "".format(dlrn_hash, candidate_label, target_label,
                                 hash_type))

        promotion_hash_list = []

        if hash_type is DlrnCommitDistroHash:
            self.log.debug("Dlrn promote '{}' from {} to {}: "
                           "adding '{}' to promotion list for single pipeline"
                           "".format(dlrn_hash, candidate_label,
                                     target_label,
                                     dlrn_hash))
            promotion_hash_list.append(dlrn_hash)

        elif hash_type is DlrnAggregateHash:
            # Aggregate hash cannot be promoted directly, we need to promote
            # all the components the aggregate points to singularly

            # Aggregate promotion step 1: download the full delorean repo
            # and save it locally for parsing
            candidate_url = ("{}/{}/delorean.repo"
                             "".format(self.config.repo_url, candidate_label))
            self.log.debug("Dlrn promote '{}': URL for candidate label "
                           "repo: {}"
                           "".format(dlrn_hash, candidate_url))
            # FIXME: in python2 urlopen is not a context manager
            try:
                with contextlib.closing(url.urlopen(candidate_url)) as \
                        remote_repo_content:
                    # FIXME: in python2 configparser can read a config only from
                    #  a file or a file-like obj. But python3 need the file
                    #  to be converted first in UTF-8
                    remote_repo_content = remote_repo_content.read().decode()
            except url.HTTPError:
                self.log.error("Dlrn Promote: Error downloading delorean repo"
                               " at %s", candidate_url)
                self.log.error("------- -------- Promoter aborted")
                raise PromotionError("Unable to fetch repo from repo url")
            # Tried to use stringIO here, but the config.readfp seems not
            # to be working correctly with stringIO, so a temporary file
            # is needed
            __, repo_file_path = tempfile.mkstemp()
            repo_config = ini_parser.ConfigParser()
            with open(repo_file_path, "w+") as repo_file:
                repo_file.write(remote_repo_content)
                repo_file.seek(0)
                # FIXME python3 can read from a string, doesn't need a fp
                repo_config.readfp(repo_file)
            os.unlink(repo_file_path)

            # AP step2: for all the subrepos in repo file get the baseurl for
            # all the components
            components = repo_config.sections()
            if not components:
                self.log.error("Dlrn promote '{}' from {} to {}: dlrn "
                               "aggregate repo at {} contains no components"
                               "".format(dlrn_hash, candidate_label,
                                         target_label,
                                         candidate_url))
                raise PromotionError("DLRN aggregate repo is empty")
            else:
                self.log.info("Dlrn promote '{}' from {} to {}: dlrn "
                              "aggregate repo at {} contains components {}"
                              "".format(dlrn_hash, candidate_label,
                                        target_label,
                                        candidate_url, components))

            # AP step3 download commits information for all the single
            # component
            for component in components:
                base_url = repo_config.get(component, 'baseurl')
                self.log.debug("Dlrn promote '{}' from {} to {}: base url url"
                               "for component {} at {}"
                               "".format(dlrn_hash, candidate_label,
                                         target_label,
                                         component, base_url))
                commits_url = "{}/{}".format(base_url, "commit.yaml")
                self.log.debug("Dlrn promote '{}' from {} to {}: commit info "
                               "url for component {} at {}"
                               "".format(dlrn_hash, candidate_label,
                                         target_label,
                                         component, commits_url))
                # FIXME: in python2 urlopen is not a context manager
                with contextlib.closing(url.urlopen(commits_url)) as \
                        commits_yaml:
                    commits = yaml.safe_load(commits_yaml.read().decode(
                        "UTF-8"))
                # AP step4: from commits.yaml extract commit/distro_hash to
                # promote and create an Hash object
                promotion_info = commits['commits'][0]
                promotion_info['timestamp'] = promotion_info['dt_commit']
                self.log.debug("Dlrn promote '{}' from {} to {}: "
                               "component '{}' commit info: {}"
                               "".format(dlrn_hash, candidate_label,
                                         target_label,
                                         component, promotion_info))

                # AP step5: add hashes to promotion list
                promotion_hash = DlrnCommitDistroHash(source=promotion_info)
                self.log.debug("Dlrn promote '{}' from {} to {}: "
                               "adding '{}' to promotion list"
                               "".format(dlrn_hash, candidate_label,
                                         target_label,
                                         promotion_hash))
                promotion_hash_list.append(promotion_hash)

            # Promote in the same order the components were promoted
            # initially
            promotion_hash_list.sort(key=lambda x: x.timestamp)

        # From this point code is the same for both types of promotions
        if not promotion_hash_list:
            self.log.error("Dlrn promote '{}' from {} to {}: No hashes ended "
                           "up in the list to promote"
                           "".format(dlrn_hash, candidate_label,
                                     target_label))
            raise PromotionError("Dlrn promote: No hashes to promote")

        for promotion_hash in promotion_hash_list:
            params = copy.deepcopy(self.promote_params)
            promotion_hash.dump_to_params(params)
            params.promote_name = target_label
            try:
                promoted_info = self.api_instance.api_promote_post(params)
                # The promoted info will sometimes return the aggregate,
                # and always the timestamp
                # but we'll always be interested in comparing just commit and
                # distro hashes
                promoted_info.timestamp = None
                stored_timestamp = promotion_hash.timestamp
                promotion_hash.timestamp = None
                promoted_hash = DlrnCommitDistroHash(source=promoted_info)
            except ApiException as ae:
                message = ae.body
                try:
                    body = json.loads(ae.body)
                    message = body['message']
                except JSONDecodeError:
                    pass
                self.log.error(
                    "Exception while promoting hashes to API endpoint "
                    "({}) {}: {}"
                    "".format(ae.status, ae.reason, message))
                self.log.error("------- -------- Promoter aborted")
                raise

            # This seemingly stupid check already helped find at least 3 bugs
            # in code and tests.
            if promoted_hash == promotion_hash:
                self.log.info("Dlrn promote '{}' from {} to {}: Successfully "
                              "promoted"
                              "".format(promotion_hash, candidate_label,
                                        target_label))
            else:
                self.log.error(
                    "Dlrn promote '{}' from {} to {}: API returned different "
                    "promoted hash: '{}'"
                    "".format(promotion_hash, candidate_label,
                              target_label, promoted_hash))
                raise PromotionError("API returned different promoted hash")

            # For every hash promoted, we need to update the named hashes.
            self.update_current_named_hashes(promotion_hash,
                                             target_label)
            # Add back timestamp
            promotion_hash.timestamp = stored_timestamp

    def vote(self, dlrn_hash, job_id, job_url, vote):
        """
        Add a CI vote for a job for a certain hash
        This method is used mainly in staging environment to create basic
        promotions to handle
        :param dlrn_hash: The hash with the info for promotion
        :param job_id: The name of the job that votes
        :param job_url: The url of the job that votes
        :param vote: A bool representing success(true) or failure(false)
        :return:  the API response after voting
        """
        params = copy.deepcopy(self.report_params)

        if type(dlrn_hash) == DlrnCommitDistroHash:
            dlrn_hash.dump_to_params(params)
        elif type(dlrn_hash) == DlrnAggregateHash:
            # votes for the aggregate hash cannot contain commit and distro
            params.aggregate_hash = dlrn_hash.aggregate_hash

        params.success = str(vote)
        params.timestamp = dlrn_hash.timestamp
        params.job_id = job_id

        params.url = job_url

        self.log.debug("Dlrn voting success: {} for dlrn_hash {}"
                       "".format(vote, dlrn_hash))
        self.log.info("Dlrn voting success: {} with parameters {}"
                      "".format(vote, job_id, params))
        try:
            api_response = self.api_instance.api_report_result_post(params)
            self.log.info("Dlrn voted success: {} for job {} on hash {}"
                          "".format(vote, job_id, dlrn_hash))
        except ApiException as ae:
            message = ae.body
            try:
                body = json.loads(ae.body)
                message = body['message']
            except JSONDecodeError:
                pass
            self.log.error("Dlrn voting success: {} for dlrn_hash {}: Error "
                           "during voting through API: ({}) {}: {}"
                           "".format(vote, dlrn_hash, ae.status, ae.reason,
                                     message))
            self.log.error("------- -------- Promoter aborted")
            raise

        if not api_response:
            self.log.error("Dlrn voting success: {} for dlrn_hash {}: API "
                           "vote response is empty"
                           "".format(vote, dlrn_hash))
            self.log.error("------- -------- Promoter aborted")
            raise PromotionError("Dlrn Vote failed")

        return api_response

    def get_civotes_info(self, dlrn_hash):
        """
        This method assembles information on where to find ci votes for a
        specific dlrn hash
        :param dlrn_hash: The dlrn hash to get info for.
        :return: A string with an url to fetch info from
        """
        civotes_info = ""
        hash_type = type(dlrn_hash)
        if hash_type is DlrnCommitDistroHash:
            civotes_info = ("Check results at: "
                            "{}/api/civotes_detail.html?"
                            "commit_hash={}&distro_hash=%{}"
                            "".format(self.config.api_url,
                                      dlrn_hash.commit_hash,
                                      dlrn_hash.distro_hash))
        elif hash_type is DlrnAggregateHash:
            civotes_info = ("Check results at: "
                            "{}/api/civotes_agg_detail.html?"
                            "ref_hash={}"
                            "".format(self.config.api_url,
                                      dlrn_hash.aggregate_hash))
        else:
            self.log.error("Unknown hash type: {}".format(hash_type))

        return civotes_info
