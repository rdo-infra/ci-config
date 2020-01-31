"""
This file contains classes and methods to interact with dlrn servers
"""
import copy
import datetime
import dlrnapi_client
import logging

from dlrnapi_client.rest import ApiException


class HashChangedError(Exception):
    """
    Raised when hashes change during a promotion
    """
    pass


class DlrnHashError(Exception):
    """
    Raised on various errors on DlrnHash operations
    """
    pass


class DlrnHashBase(object):

    log = logging.getLogger("promoter")

    def __init__(self, source):
        self.commit_hash = None
        self.distro_hash = None
        self.aggregated_hash = None
        self.timestamp = None
        # load from unified source
        for key, value in source.items():
            setattr(self, key, value)

        # Sanity checks
        # Check that all hash are not present
        if (self.commit_hash is not None
            or self.distro_hash is not None) \
                and self.aggregated_hash is not None:
            raise DlrnHashError("commit, distro and aggregated hashes must"
                                " NOT be specified all together")
        # TODO(gcerami) strict dlrn validation: check that the hashes are valid
        # hashes with correct size

        # Maybe we could implement with __getattribute__(__class__)
        # or using metaclasses ?
        self.hash_type = type(self)


class DlrnCommitDistroHash(DlrnHashBase):

    def __repr__(self):
        return ("<DlrnHash object commit: %s, distro: %s, timestamp: %s>"
                "" % (self.commit_hash, self.distro_hash, self.timestamp))

    def __str__(self):
        return ("commit: %s, distro: %s, timestamp=%s"
                "" % (self.commit_hash, self.distro_hash, self.timestamp))

    def __ne__(self, other):

        try:
            result = (self.commit_hash != other.commit_hash
                      or self.distro_hash != other.distro_hash
                      or self.timestamp != other.timestamp)
        except AttributeError:
            raise TypeError("Cannot compare {} with {}"
                            "".format(type(self), type(other)))

        return result

    def __eq__(self, other):

        try:
            result = (self.commit_hash == other.commit_hash
                      and self.distro_hash == other.distro_hash
                      and self.timestamp == other.timestamp)
        except AttributeError:
            raise TypeError("Cannot compare {} with {}"
                            "".format(type(self), type(other)))

        return result

    @property
    def full_hash(self):
        """
        Property to abstract the common representation of a full dlrn hash
        containing full commit and abbreviated distro hashes
        Work only with single norma dlrn haseh
        :return:  The full hash format or None
        """
        return '{0}_{1}'.format(self.commit_hash, self.distro_hash[:8])

    def key(self):
        """
        Most of the code that uses hashes, rely on an identifier of the hash to
        use as key in dictionaries
        The key will differ for single or aggregated hashes
        :return: full hash for single or aggregated_hash for aggregated
        """
        return self.full_hash

    def dump_to_dict(self):
        """
        dumps the hash into a dict
        :return: A dict
        """
        result = dict(
            commit_hash=self.commit_hash,
            distro_hash=self.distro_hash,
            full_hash=self.full_hash,
            timestamp=self.timestamp,
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
        params.timestamp = self.timestamp


class DlrnAggregatedHash(DlrnHashBase):

    def __repr__(self):
        return ("<DlrnAggregatedHash object aggregated: %s, timestamp: %s>"
                "" % (self.aggregated_hash, self.timestamp))

    def __str__(self):
        return ("aggregated: %s, timestamp=%s"
                "" % (self.aggregated_hash, self.timestamp))

    def __eq__(self, other):

        try:
            result = (self.aggregated_hash == other.aggregated_hash
                      and self.timestamp == other.timestamp)
        except AttributeError:
            raise TypeError("Cannot compare {} with {}"
                            "".format(type(self), type(other)))

        return result

    def __ne__(self, other):
        try:
            result = (self.aggregated_hash != other.aggregated_hash
                      or self.timestamp != other.timestamp)
        except AttributeError:
            raise TypeError("Cannot compare {} with {}"
                            "".format(type(self), type(other)))

        return result

    @property
    def full_hash(self):
        """
        Property to abstract the common representation of a full dlrn hash
        In aggregated hash th full_hash is the aggregated hash itself
        :return:  The aggregated hash
        """
        return self.aggregated_hash

    def dump_to_dict(self):
        """
        dumps the hash into a dict
        :return: A dict
        """
        result = dict(
            aggregated_hash=self.full_hash,
            timestamp=self.timestamp,
        )
        return result

    def dump_to_params(self, params):
        """
        Takes a dlrn api params object and dumps the hash informations into it
        :param params: The params object to fill
        :return: None
        """
        params.aggregated_hash = self.aggregated_hash
        params.timestamp = self.timestamp


class DlrnHash(object):
    """
    Proxy class
    This class represent the dlrn hash, It makes it easier to handle, compare
    and visualize dlrn hashes
    It's a polymorphic class as it can be used as the Dlrn hash for the single
    pipeline or as a Dlrn aggregated hash for the component pipeline
    """

    log = logging.getLogger("promoter")

    def __init__(self, commit_hash=None, distro_hash=None, timestamp=None,
                 aggregated_hash=None, source=None):
        """
        Dlrn Hash can be initialized either by direct kwargs value, from a
        dictionary, or from a dlrn api response object
        :param commit: the direct commit hash
        :param distro:  the direct distro hash
        :param aggregated: the direct aggregated_hash
        :param timstamp: the direct timestamp value, must be float
        :param source: A valid dlrn api response object or a dictionary
        that needs to contain *_hash as keys
        """
        # Load from default values into unified source
        _source = {}
        _source['commit_hash'] = commit_hash
        _source['distro_hash'] = distro_hash
        _source['timestamp'] = timestamp
        _source['aggregated_hash'] = aggregated_hash

        # Checks on sources
        valid_attributes = set(['commit_hash', 'distro_hash', 'aggregated_hash',
                                'timestamp'])
        source_attributes = dir(source)
        valid_source_object = bool(valid_attributes.intersection(
            source_attributes))

        # Gather Sources
        if source is not None and isinstance(source, dict):
            # source is dict, use dict to update unified source
            _source.update(source)

        elif source is not None and valid_source_object:
            # try loading from object convert to dict and update the unified
            # source
            __source = {}
            for attribute in valid_attributes:
                try:
                    __source[attribute] = getattr(source, attribute)
                except AttributeError:
                    pass

            _source.update(__source)
        elif source is not None:
            raise DlrnHashError("Cannot build: invalid source object {}"
                                "".format(source))

        self._hash_instance = None
        # Are we single or aggregated ?
        if _source['commit_hash'] is not None \
           and _source['distro_hash'] is not None:
            # if it has commit and distro is a normal hash
            self._hash_instance = DlrnCommitDistroHash(_source)
        elif _source['aggregated_hash'] is not None:
            # if it has aggregated_hash it's an aggregated hash
            # (..duh!)
            self._hash_instance = DlrnAggregatedHash(_source)
        else:
            raise DlrnHashError("Cannot build: all values are empty")

    def __class__(self):
        return type(self._hash_instance)

    def __getattr__(self, name):
        # As each proxy instance will be tied to a single proxied class
        # and we assume that all the subclasses will have the same interface
        # we use a static selection here
        attr = getattr(self._hash_instance, name)
        return attr

    def __eq__(self, other):
        """
        Manual proxy method as __getattr__ is bypassed for magic methods
        """
        return self._hash_instance.__eq__(other)

    def __ne__(self, other):
        """
        Manual proxy method as __getattr__ is bypassed for magic methods
        """
        return self._hash_instance.__ne__(other)

    def __str__(self):
        """
        Manual proxy method as __getattr__ is bypassed for magic methods
        """
        return self._hash_instance.__str__()

    def __repr__(self):
        """
        Manual proxy method as __getattr__ is bypassed for magic methods
        """
        return self._hash_instance.__repr__()


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

        # Variable to detect changes on the hash while we are running a
        # promotion
        self.named_hashes_map = {}

        # This way of preparing parameters and configuration is copied
        # directly from dlrnapi CLI and ansible module
        self.hashes_params = dlrnapi_client.PromotionQuery()
        self.jobs_params = dlrnapi_client.Params2()
        self.promote_params = dlrnapi_client.Promotion()

    def update_current_named_hashes(self, hash, label):
        self.named_hashes_map.update({label: hash.full_hash})

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
            update = {promote_name: latest_named.full_hash}
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
            hash_obj = DlrnHash(source=hashes)
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
            api_hashes = self.api_instance.api_promotions_get(params)
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

        self.log.debug(
            'Fetch Hashes: fetched %d hashes for name %s: %s',
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
