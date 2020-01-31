import logging


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
        return ("commit: %s, distro: %s, component: %s, timestamp: %s"
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
