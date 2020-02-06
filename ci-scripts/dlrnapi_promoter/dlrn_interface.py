"""
This file contains classes and methods to interact with dlrn server
dlrn configuration options, dlrn repos
"""
import contextlib
import copy
import datetime
import dlrnapi_client
import logging
import pprint
import json
import yaml
import tempfile

try:
    import urllib2 as url
except ImportError:
    import urllib.request as url
try:
    import ConfigParser as ini_parser
except ImportError:
    import configparser as ini_parser

try:
    import StringIO as sio
except ImportError:
    import io as sio

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


# TODO(gcerami) we could use functools.total_ordering here
class DlrnHashBase(object):
    """
    THis is the base abstract class for all type of hashes
    It represents the dlrn hash, It makes it easier to handle, compare
    and visualize dlrn hashes
    It should never be instantiated directly
    """

    log = logging.getLogger("promoter")

    def __init__(self, commit_hash=None, distro_hash=None, timestamp=None,
                 aggregate_hash=None, source=None, component=None):
        """
        Takes care of filling the hash attributes from the instantiation
        parameters.
        Also implements sanity checks on the parameters
        :param commit_hash:  the commit part of the hash
        :param distro_hash: the distro part of the hash
        :param timestamp: the timestamp of the hash
        :param aggregate_hash: the computed aggregated part of the hash
        :param source: a dictionary with all the parameters as keys
        :param component:  the eventual component of the hash
        """
        # Load from default values into unified source
        _source = {}
        _source['commit_hash'] = commit_hash
        _source['distro_hash'] = distro_hash
        _source['timestamp'] = timestamp
        _source['dt_commit'] = timestamp
        _source['aggregate_hash'] = aggregate_hash
        _source['component'] = component

        # Checks on sources
        valid_attributes = {'commit_hash', 'distro_hash', 'aggregate_hash',
                            'timestamp', 'component'}
        source_attributes = dir(source)
        valid_source_object = bool(valid_attributes.intersection(
            source_attributes))

        # Gather Sources
        if source is not None and isinstance(source, dict):
            # source is dict, use dict to update unified source
            for attribute in valid_attributes:
                try:
                    _source[attribute] = source[attribute]
                except KeyError:
                    pass

        elif source is not None and valid_source_object:
            # try loading from object convert to dict and update the unified
            # source
            for attribute in valid_attributes:
                try:
                    _source[attribute] = getattr(source, attribute)
                except AttributeError:
                    pass

        elif source is not None:
            raise DlrnHashError("Cannot build: invalid source object {}"
                                "".format(source))

        # load from unified source
        for key, value in _source.items():
            setattr(self, key, value)

        self.sanity_check()

        # TODO(gcerami) strict dlrn validation: check that the hashes are valid
        # hashes with correct size

    @property
    def commit_dir(self):
        """
        Computes the commit path related to the hash in a dlrn repo
        in the format XY/XY/XYZTR
        :return: The computed path
        """
        return "{}/{}/{}".format(self.commit_hash[:2], self.commit_hash[2:4],
                                 self.full_hash)


class DlrnCommitDistroHash(DlrnHashBase):
    """
    This class implements methods for the commit/distro dlrn hash
    for the single pipeline
    It inherits from the base class and does not override the init
    """

    def sanity_check(self):
        """
        Checks if the basic components of the hash are present
        component and timestamp are optional
        """
        if self.commit_hash is None or self.distro_hash is None:
            raise DlrnHashError("Invalid commit or distro hash")

    def __repr__(self):
        """
        implements special method to output the hash information
        useful for logging and debugging
        :return: The string representation of the object
        """
        return ("<DlrnCommitDistroHash object commit: %s,"
                " distro: %s, component: %s, timestamp: %s>"
                "" % (self.commit_hash, self.distro_hash,
                      self.component, self.timestamp))

    def __str__(self):
        """
        implements special method to output the hash information
        useful for logging and debugging
        :return: The string representation of the hash informations
        """
        return ("commit: %s, distro: %s, component: %s, timestamp=%s"
                "" % (self.commit_hash, self.distro_hash,
                      self.component, self.timestamp))

    def __ne__(self, other):
        """
        Implement special methods of comparison with other object if compatible.
        Raises error if not.
        :param other: The object to compare self to
        :return: bool
        """
        try:
            result = (self.commit_hash != other.commit_hash
                      or self.distro_hash != other.distro_hash
                      or self.component != other.component
                      or self.timestamp != other.timestamp)
        except AttributeError:
            raise TypeError("Cannot compare {} with {}"
                            "".format(type(self), type(other)))

        return result

    def __eq__(self, other):
        """
        Implement special methods of comparison with other object if compatible.
        Raises error if not.
        :param other: The object to compare self to
        :return: bool
        """
        try:
            result = (self.commit_hash == other.commit_hash
                      and self.distro_hash == other.distro_hash
                      and self.component == other.component
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

    def dump_to_dict(self):
        """
        dumps the hash into a dict
        :return: A dict
        """
        result = dict(
            commit_hash=self.commit_hash,
            distro_hash=self.distro_hash,
            full_hash=self.full_hash,
            component=self.component,
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
        params.component = self.component
        params.timestamp = self.timestamp


class DlrnAggregateHash(DlrnHashBase):
    """
    This class implements methods for the aggregate hash
    for the component pipeline
    It inherits from the base class and does not override the init
    """

    def sanity_check(self):
        """
        Checks if the basic components of the hash are present
        component and timestamp are optional
        """
        if self.commit_hash is None or self.distro_hash is None or \
                self.aggregate_hash is None:
            raise DlrnHashError("Invalid commit or distro or aggregate_hash")

    def __repr__(self):
        """
        implements special method to output the hash information
        useful for logging and debugging
        :return: The string representation of the object
        """
        return ("<DlrnAggregateHash object aggregate: %s, commit: %s,"
                " distro: %s, component: %s, timestamp: %s>"
                "" % (self.aggregate_hash, self.commit_hash, self.distro_hash,
                      self.component, self.timestamp))

    def __str__(self):
        """
        implements special method to output the hash information
        useful for logging and debugging
        :return: The string representation of the hash informations
        """
        return ("aggregate: %s, commit: %s,"
                " distro: %s, component: %s, timestamp: %s"
                "" % (self.aggregate_hash, self.commit_hash, self.distro_hash,
                      self.component, self.timestamp))

    def __eq__(self, other):
        """
        Implement special methods of comparison with other object if compatible.
        Raises error if not.
        :param other: The object to compare self to
        :return: bool
        """

        try:
            result = (self.aggregate_hash == other.aggregate_hash
                      and self.commit_hash == other.commit_hash
                      and self.distro_hash == other.distro_hash
                      and self.timestamp == other.timestamp)
        except AttributeError:
            raise TypeError("Cannot compare {} with {}"
                            "".format(type(self), type(other)))

        return result

    def __ne__(self, other):
        """
        Implement special methods of comparison with other object if compatible.
        Raises error if not.
        :param other: The object to compare self to
        :return: bool
        """
        try:
            result = (self.aggregate_hash != other.aggregate_hash
                      or self.commit_hash != other.commit_hash
                      or self.distro_hash != other.distro_hash
                      or self.timestamp != other.timestamp)
        except AttributeError:
            raise TypeError("Cannot compare {} with {}"
                            "".format(type(self), type(other)))

        return result

    @property
    def full_hash(self):
        """
        Property to abstract the common representation of a full dlrn hash
        In aggregate hash th full_hash is the aggregate hash itself
        :return:  The aggregate hash
        """
        return self.aggregate_hash

    def dump_to_dict(self):
        """
        dumps the hash into a dict
        :return: A dict
        """
        result = dict(
            aggregate_hash=self.full_hash,
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
        params.aggregate_hash = self.aggregate_hash
        params.commit_hash = self.commit_hash
        params.distro_hash = self.distro_hash
        params.timestamp = self.timestamp


class DlrnHash(object):
    """
    This is the metaclass that creates and returns the instance of
    the class equivalent to the hash type handled. It can be return a
    Dlrn hash for the single pipeline or a Dlrn aggregate hash for the
    component pipeline It allows the DlrnHashBase class to be polymorhic,
    and work transparently for the caller as it does not have to worry if
    the hash is for the single or the component pipelines
    """

    log = logging.getLogger("promoter")

    def __new__(cls, **kwargs):
        """
        Dlrn Hash can be initialized either by direct kwargs value, from a
        dictionary, or from a dlrn api response object
        :param commit: the direct commit hash
        :param distro:  the direct distro hash
        :param aggregate: the direct aggregate_hash
        :param timstamp: the direct timestamp value, must be float
        :param source: A valid dlrn api response object or a dictionary
        that needs to contain *_hash as keys
        """
        hash_instance = DlrnCommitDistroHash(**kwargs)

        try:
            if kwargs['aggregate_hash'] is not None:
                hash_instance = DlrnAggregateHash(**kwargs)
        except KeyError:
            try:
                if kwargs['source']['aggregate_hash'] is not None:
                    hash_instance = DlrnAggregateHash(**kwargs)
            except (TypeError, KeyError):
                try:
                    if kwargs['source'].aggregate_hash is not None:
                        hash_instance = DlrnAggregateHash(**kwargs)
                except (KeyError, AttributeError):
                    pass

        return hash_instance


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
        self.log.info('Using API URL: %s', api_client.host)
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
            latest_named = self.fetch_promotions(promote_name, count=1)
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
        print(latest_named_hashes, self.named_hashes_map)
        if latest_named_hashes != self.named_hashes_map:
            self.log.error('ERROR: Aborting promotion named hashes changed '
                           'since promotion started. Hashes at start: %s.'
                           'Hashes now: %s ',
                           self.named_hashes_map, latest_named_hashes)
            raise HashChangedError("Named Hashes Changed!")

    def fetch_jobs(self, dlrn_hash):
        """
        This method fetch a list of successful jobs from a dlrn server for a
        specific hash identifier.
        :param dlrn_id: The dlrn identifier to fetch jobs from. It could be
        either a DlrnHash or a DlrnAggregateHash
        :return: A list of job ids (str)
        """

        if type(dlrn_hash) == DlrnCommitDistroHash:
            api_call = self.api_instance.api_repo_status_get
            jobs_params = self.jobs_params
        elif type(dlrn_hash) == DlrnAggregateHash:
            api_call = self.api_instance.api_agg_status_get
            jobs_params = self.jobs_params_aggregate

        params = copy.deepcopy(jobs_params)
        dlrn_hash.dump_to_params(params)
        params.success = str(True)

        try:
            api_response = api_call(params)
        except ApiException as ae:
            body = json.loads(ae.body)
            self.log.error('Exception while fetching jobs from API endpoint '
                           '(%s) %s: %s'
                           '', ae.status, ae.reason, body['message'])
            raise

        self.log.debug('Successful jobs for %s:', str(dlrn_hash))
        for result in api_response:
            self.log.debug('%s at %s, logs at "%s"', result.job_id,
                           datetime.datetime.fromtimestamp(
                               result.timestamp).isoformat(),
                           result.url)

        return [details.job_id for details in api_response]

    @staticmethod
    def hashes_to_hashes(api_hashes, remove_duplicates=False):
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
        hash_list = self.fetch_hashes(params, count=count)
        if type(hash_list) == list:
            hashes = len(hash_list)
        else:
            hashes = 1
        self.log.debug(
            'Fetch Hashes: fetched %d hashes for name %s: %s',
            hashes, label, hash_list)
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

        try:
            # API documentation says the hashes are returned in reverse
            # timestamp order (from newest to oldest) by defaut
            api_hashes = self.api_instance.api_promotions_get(params)
            hash_list = self.hashes_to_hashes(api_hashes,
                                              remove_duplicates=True)
        except ApiException:
            self.log.error('Exception while getting hashes list '
                           'through api', ApiException)
            raise

        if sort == "timestamp" and reverse is not None:
            hash_list.sort(key=lambda hashes: hashes.timestamp, reverse=reverse)

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
                try:
                    self._promote_hash(incumbent_hash, previous_target_label,
                                       candidate_label=target_label)
                except ApiException:
                    self.log.error('unable to store current hashes as previous',
                                   ApiException)
                    raise

        self.log.info("Promoting hash {} to {} in DLRN "
                      "".format(dlrn_hash, target_label))
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
        self.log.info("Promoting {} from {} to {}".format(dlrn_hash,
                                                          candidate_label,
                                                          target_label))
        promotion_hash_list = []
        if type(dlrn_hash) == DlrnAggregateHash:
            # Aggregate hash cannot be promoted directly, we need to promote
            # all the components the aggregate points to singularly
            # Aggregate promotion step 1: download the full delorean repo
            # and save it locally for parsing
            repo_url = "https://trunk.rdoproject.org/centos8-master"
            candidate_url = "{}/{}/delorean.repo".format(repo_url,
                                                    candidate_label)
            repo_config = ini_parser.ConfigParser()
            # FIXME: in python2 urlopen is not a context manager
            self.log.debug("Candidate URL: {}".format(candidate_url))
            # Tried stringIO here, but the config.readfp seems not to be
            # working correctly with stringIO, so a temporary file is needed
            __, repo_file_path = tempfile.mkstemp()
            repo_file = open(repo_file_path, "w+")
            with contextlib.closing(url.urlopen(candidate_url)) as \
                    remote_repo_file:
                # FIXME: in python2 configparser can read a config only from
                # a file or a file-like obj. But python3 need the file to be
                # converted first in UTF-8
                repo_file.write(remote_repo_file.read().decode())
                repo_file.seek(0)
                repo_config.readfp(repo_file)
            # AP step2: for all the subrepos in repo file get the baseurl for
            # all the components
            for section in repo_config.sections():
                hash_info = {}
                baseurl = repo_config.get(section, 'baseurl')
                # AP step3 download commits information for all the single
                # component
                commits_url = "{}/{}".format(baseurl, "commit.yaml")
                with url.urlopen(commits_url) as commits_yaml:
                    commits = yaml.safe_load(commits_yaml.read().decode(
                        "UTF-8"))
                # AP step4: from commits.yaml extract commit/distro_hash to
                # promote and create an Hash object
                hash_info['commit_hash'] = commits['commits'][0]['commit_hash']
                hash_info['distro_hash'] = commits['commits'][0]['distro_hash']
                hash_info['component'] = commits['commits'][0]['component']
                hash_info['timestamp'] = commits['commits'][0]['dt_commit']
                promotion_hash = DlrnCommitDistroHash(source=hash_info)
                # AP step5: add hashes to promotion list
                self.log.debug("Adding {} to the list of chashes to promote".format(promotion_hash))
                promotion_hash_list.append(promotion_hash)

            # Promote in the same order the components were promoted
            # initially
            promotion_hash_list.sort(key=lambda x: x.timestamp)

        elif type(dlrn_hash) == DlrnCommitDistroHash:
            promotion_hash_list.append(dlrn_hash)

        # This part is the same for both promotions
        for promotion_hash in promotion_hash_list:
            params = copy.deepcopy(self.promote_params)
            promotion_hash.dump_to_params(params)
            params.promote_name = target_label
            try:
                self.api_instance.api_promote_post(params)
                self.log.info("Promoted {} to {}".format(params, target_label))
            except ApiException:
                self.log.error('Exception when calling api_promote_post: '
                               '%s', ApiException)
                raise

    def vote(self, dlrn_hash, job_id, job_url, vote):
        """
        Add a CI vote for a job for a certain hash
        This method is used mainly in staging environment to create basic
        promotions to handle
        :param dlrn_hash: The hash with the info for promotion
        :param job_id: The name of the job that votes
        :param job_url: The url of the job that votes
        :param vote: A bool representing success(true) or failure(false)
        :return:  None
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

        try:
            api_response = self.api_instance.api_report_result_post(params)
        except ApiException as ae:
            body = json.loads(ae.body)
            self.log.error('Exception while voting on API endpoint '
                           '(%s) %s: %s'
                           '', ae.status, ae.reason, body['message'])
            raise

        return api_response

    def get_civotes_info(self, dlrn_hash):
        """
        This method assembles information on where to find ci votes for a
        specific dlrn hash
        :param dlrn_hash: The dlrn hash to get info for.
        :return: A string with an url to fetch info from
        """
        if hasattr(dlrn_hash, 'commit_hash'):
            civotes_info = ('%s \n%s/api/civotes_detail.html?'
                            'commit_hash=%s&distro_hash=%s'.replace(" ", ""),
                            'DETAILED FAILED STATUS: ',
                            self.config.api_url,
                            dlrn_hash.commit_hash,
                            dlrn_hash.distro_hash)
            return civotes_info
        elif self.config.pipeline_type == "component":
            self.log.error("Component pipeline ci votes information is not yet "
                           "available")
