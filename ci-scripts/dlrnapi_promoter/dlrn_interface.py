"""
This file contains classes and methods to interact with dlrn servers
"""
import copy
import datetime
import dlrnapi_client
import logging

from dlrnapi_client.rest import ApiException
from legacy_promoter import promote_link


class HashChangedError(Exception):
    pass


class DlrnAggregatedHash(str):
    """
    This class represents the aggregate hash for the component pipeline
    Not yet implemented
    """
    log = logging.getLogger("promoter")

    def __init__(self, aggregated_hash):
        pass

    def dump_to_params(self):
        pass


class DlrnHash(dict):
    """
    This class represent the dlrn hash, It makes it easier to handle, compare
    and visualize dlrn hashes
    """

    log = logging.getLogger("promoter")

    def __init__(self, commit=None, distro=None, timestamp=None, from_api=None,
                 from_dict=None):
        """
        Dlrn Hash can be initialized either by direct kwargs value, from a
        dictionary, or from a dlrn api response object
        :param commit: the direct commit hash
        :param distro:  the direct distro hash
        :param timstamp: the direct timestamp value, must be float
        :param from_api: A valid dlrn api response object
        :param from_dict:  A dictionary that needs to contain commit_hash and
        distro_hash as keys
        """
        self.commit_hash = ""
        self.distro_hash = ""
        self.timestamp = timestamp
        if from_api is not None:
            try:
                self.commit_hash = from_api.commit_hash
                self.distro_hash = from_api.distro_hash
                if hasattr(from_api, "timestamp"):
                    self.timestamp = from_api.timestamp
            except AttributeError:
                raise AttributeError("Error while building DlrnHash:"
                                     " invalid source API object")
        elif from_dict is not None:
            try:
                self.commit_hash = from_dict['commit_hash']
                self.distro_hash = from_dict['distro_hash']
                if "timestamp" in from_dict:
                    self.timestamp = from_dict['timestamp']
            except KeyError:
                raise KeyError("Error while building DlrnHash:"
                               " invalid source dict")
        elif commit is not None and distro is not None:
            self.commit_hash = commit
            self.distro_hash = distro
        else:
            self.log.debug("Creating empty DlrnHash")

        # TODO(gcerami) strict dlrn validation
        # check that the hashes are valid hashes with correct size

    def __eq__(self, other):
        if not hasattr(other, 'commit_hash') or \
                not hasattr(other, 'distro_hash') or \
                not hasattr(other, 'timestamp'):
            raise TypeError("One of the objects is not a valid DlrnHash")

        return (self.commit_hash == other.commit_hash
                and self.distro_hash == other.distro_hash
                and self.timestamp == other.timestamp)

    def __ne__(self, other):
        if not hasattr(other, 'commit_hash') or \
                not hasattr(other, 'distro_hash') or \
                not hasattr(other, 'timestamp'):
            raise TypeError("One of the objects is not a valid DlrnHash")

        return (self.commit_hash != other.commit_hash
                or self.distro_hash != other.distro_hash
                or self.timestamp != other.timestamp)

    def __str__(self):
        return ("commit: %s, distro: %s, timestamp=%s"
                "" % (self.commit_hash, self.distro_hash, self.timestamp))

    def __repr__(self):
        return ("<DlrnHash object commit: %s, distro: %s, timestamp: %s>"
                "" % (self.commit_hash, self.distro_hash, self.timestamp))

    @property
    def id(self):
        return self.full_hash

    @property
    def full_hash(self):
        """
        Property to abstract the common representation of a full dlrn hash
        containing full commit and abbreviated distro hashes
        :return:  The full hash format
        """
        return '{0}_{1}'.format(self.commit_hash, self.distro_hash[:8])

    def dump_to_dict(self):
        """
        dumps the hash into a dict
        :return: A dict
        """
        result = dict(
            commit_hash=self.commit_hash,
            distro_hash=self.distro_hash,
            full_hash=self.full_hash,
        )
        return result

    def dump_to_params(self, params):
        """
        Takes a dlrn api params object and dumps the hash informations into it
        :param params: The params object to fill
        :return: None
        """
        params.commit_hash = self.commit_hash
        params.distro_hash = self.distro_hash


class DlrnClient(object):
    """
    This class represent a wrapper around dlrnapi client operations to perform
    complex operations on hashes
    """

    log = logging.getLogger("promoter")

    def __init__(self, config):
        self.config = config
        # TODO(gcerami): fix credentials gathering
        dlrnapi_client.configuration.password = self.config.dlrnauth_password
        dlrnapi_client.configuration.username = self.config.dlrnauth_username
        api_client = dlrnapi_client.ApiClient(host=self.config.api_url)
        self.api_instance = dlrnapi_client.DefaultApi(api_client=api_client)
        self.log.info('Using API URL: %s', api_client.host)
        self.last_promotions = {}

        # Sets variables and object depending on the pipeline type
        if self.config.pipeline_type == "single":
            self.hash_class = DlrnHash
            # This way of preparing parameters and configuration is copied
            # directly from dlrnapi CLI and ansible module
            self.hashes_params = dlrnapi_client.PromotionQuery()
            self.jobs_params = dlrnapi_client.Params2()
            self.promote_params = dlrnapi_client.Promotion()
            self.promotions_get = self.api_instance.api_promotions_get
        elif self.config.pipeline_type == "component":
            # Params have not been change for aggregate but api is not stable
            # yet. If they end up being the same, we can group them in the
            # section above
            self.hashes_params = dlrnapi_client.PromotionQuery()
            self.jobs_params = dlrnapi_client.Params2()
            self.promote_params = dlrnapi_client.Promotion()
            self.hash_class = DlrnAggregatedHash
            self.promotions_get = self.api_instance.api_aggregate_promotions_get
        # Variable to detect changes on the hash while we are running a
        # promotion
        self.named_hashes_map = {}

    def update_current_named_hashes(self, hash, label):
        self.named_hashes_map.update({label: hash.id})

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
            latest_named = self.fetch_hashes(promote_name, count=1,
                                             sort="timestamp", reverse=True)
            update = {promote_name: latest_named.id}
            if store:
                self.named_hashes_map.update(update)
            named_hashes.update(update)

        return named_hashes

    def check_named_hashes_unchanged(self):
        """
        Fetch latest named hashes and compare to the initial named_hashes_map
        If they are different log error and raise Exception
        :param label: The label to check for changes
        :return: None
        """
        latest_named_hashes = self.fetch_current_named_hashes()
        if latest_named_hashes != self.named_hashes_map:
            self.log.error('ERROR: Aborting promotion named hashes changed '
                           'since promotion started. Hashes at start: %s.'
                           'Hashes now: %s ',
                           self.named_hashes_map, latest_named_hashes)
            raise HashChangedError("Named Hashes Changed!")

    def fetch_jobs(self, dlrn_id):
        """
        This method fetch a list of successful jobs from a dlrn server for a
        specific hash identifier.
        :param dlrn_id: The dlrn identifier to fetch jobs from. It could be
        either a DlrnHash or a DlrnAggregatedHash
        :return: A list of job ids (str)
        """
        params = copy.deepcopy(self.jobs_params)
        dlrn_id.dump_to_params(params)
        params.success = str(True)

        try:
            api_response = self.api_instance.api_repo_status_get(params)
        except ApiException:
            self.log.error('Exception when calling api_repo_status_get: %s',
                           ApiException)
            raise

        self.log.debug('Successful jobs for %s:', dlrn_id)
        for result in api_response:
            self.log.debug('%s at %s, logs at "%s"', result.job_id,
                           datetime.datetime.fromtimestamp(
                               result.timestamp).isoformat(),
                           result.url)

        return [details.job_id for details in api_response]

    def hashes_to_hashes(self, api_hashes, remove_duplicates=False):
        """
        Converts a list of hashes provided as response from api to a list
        of DlrnHash or DlrnAggregatedHash objects
        :param api_hashes: The list of hashes to convert
        :param remove_duplicates: If true all the duplicate elements in the
        list will be removed
        :return: a list of DlrnHash or DlrnAggregateHash objects
        """
        result = []
        for hashes in api_hashes:
            hash_obj = self.hash_class(from_api=hashes)

            # we could use a set, but then we'd lose the order
            if remove_duplicates and hash_obj in result:
                continue
            result.append(hash_obj)

        return result

    def fetch_hashes(self, label, count=None, sort=None, reverse=False):
        """
        This method fetches a history of hashes that were promoted to a
        specific label, without duplicates.
        :param label: The dlrn identifier
        :param count: Limit the list to count element, If unspecified,
        all the elements will be returned
        :param sort: Sort the list by the specified supported criteria
        :param reverse: reverses sort is applied
        :return: A single hash when count=1. A list of hashes otherwise
        """
        params = copy.deepcopy(self.hashes_params)
        params.promote_name = label

        try:
            api_hashes = self.promotions_get(params)
            hash_list = self.hashes_to_hashes(api_hashes,
                                              remove_duplicates=True)
        except ApiException:
            self.log.error('Exception while getting hashes list '
                           'through api', ApiException)
            raise

        if len(hash_list) == 0:
            return None

        if sort == "timestamp":
            hash_list.sort(key=lambda hashes: hashes.timestamp, reverse=reverse)

        print(hash_list)
        self.log.debug(
            'Fetch Hashes: fetched %s hashes for name %s: %s',
            label, self.config.latest_hashes_count, hash_list)

        if count == 1:
            return hash_list[0]

        # if count is None, list[:None] will return the whole list
        return hash_list[:count]

    def promote_hash(self, hash, target_label):
        """
        This method promotes an hash identifier to a target label
        from another POV the hash is labeled as the target
        from another yet POV the label becomes a link to the hash identifier
        :param dlrn_id: The dlrn identifier to promote. Currently
        implemented only the commit/distro format. Aggregate hash is not
        implemented
        :param target_label: The label to promote the identifier to
        :return: None
        """
        incumbent_hash = self.fetch_hashes(target_label, count=1)
        # Save current hash as previous-$link
        if incumbent_hash is not None:
            params = copy.deepcopy(self.promote_params)
            incumbent_hash.dump_to_params(params)
            params.promote_name = "previous-" + target_label
            try:
                self.api_instance.api_promote_post(params)
            except ApiException:
                self.log.error(
                    'Exception when calling api_promote_post: %s'
                    ' to store current hashes as previous',
                    ApiException)
                raise
        params = copy.deepcopy(self.promote_params)
        hash.dump_to_params(params)
        params.promote_name = target_label
        try:
            self.api_instance.api_promote_post(params)
        except ApiException:
            self.log.error('Exception when calling api_promote_post: '
                           '%s', ApiException)
            raise

    def get_civotes_info(self, hash):
        """
        This method assembles information on where to find ci votes for a
        specific dlrn id
        :param dlrn_id: The dlrn identifier to get info for. Currently
        implemented only the commit/distro format. Aggregate hash is not
        implemented
        :return: A string with an url to fetch info from
        """
        if hasattr(hash, 'commit_hash'):
            civotes_info = ('%s \n%s/api/civotes_detail.html?'
                            'commit_hash=%s&distro_hash=%s'.replace(" ", ""),
                            'DETAILED FAILED STATUS: ',
                            self.config.api_url,
                            hash.commit_hash,
                            hash.distro_hash)
            return civotes_info
        elif self.config.pipeline_type == "component":
            self.log.error("Component pipeline ci votes information is not yet "
                           "available")
