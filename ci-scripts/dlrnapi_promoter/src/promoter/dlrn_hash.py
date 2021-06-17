"""
This file contains implementation of the DlrnHash object.
To reach transparency for the operation of the other elements in the
promotion on both single pipeline and integration pipeline scenarios,
the complexity of the separation and difference between the two pipelines has
been moved to dlrn sections only.
The classes here in particular implement the separation as a metaclass that
when called with information to build a dlrn hash returns the proper class
based on the information present in the source
"""
import logging


def check_hash(hash_value):
    """
    This function will check the hash function properties like
    hash size, valid hash etc.
    """
    if hash_value is not None:
        try:
            int(hash_value, 16)
            len(hash_value) == 40
        except (TypeError, ValueError):
            raise DlrnHashError("Invalid hash format!!")


def check_extended_hash(extended_hash):
    """
    This function will check valid extended hash.
    """
    if extended_hash is not None and extended_hash not in ['None', '']:
        try:
            e_hash = extended_hash.split("_")
            if len(e_hash) == 2:
                check_hash(e_hash[0])
                check_hash(e_hash[1])
            else:
                raise DlrnHashError("Invalid extended hash format")
        except (TypeError, ValueError):
            raise DlrnHashError("Invalid extended hash, not a hex hash!")


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

    def __init__(self, commit_hash=None, distro_hash=None, extended_hash=None,
                 timestamp=None, aggregate_hash=None, source=None,
                 component=None, label=None):
        """
        Takes care of filling the hash attributes from the instantiation
        parameters.
        Also implements sanity checks on the parameters
        :param commit_hash:  the commit part of the hash
        :param distro_hash: the distro part of the hash
        :param extended_hash: the extended part of the hash
        :param timestamp: the timestamp of the hash
        :param aggregate_hash: the computed aggregated part of the hash
        :param source: a dictionary with all the parameters as keys
        :param component:  the eventual component of the hash
        """
        # Make sure extended_hash value should be None not "None"
        if extended_hash in ['None', '']:
            extended_hash = None

        # Load from default values into unified source
        _source = {
            'commit_hash': commit_hash,
            'distro_hash': distro_hash,
            'extended_hash': extended_hash,
            'timestamp': timestamp,
            'dt_commit': timestamp,
            'aggregate_hash': aggregate_hash,
            'component': component,
            'label': label
        }

        # Checks on sources
        valid_attributes = {'commit_hash', 'distro_hash', 'extended_hash',
                            'aggregate_hash', 'timestamp', 'component'}
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
            if key == 'extended_hash' and value in ['', 'None']:
                setattr(self, key, None)

        self.sanity_check()

        # TODO(gcerami) strict dlrn validation: check that the hashes are valid
        # hashes with correct size


class DlrnCommitDistroExtendedHash(DlrnHashBase):
    """
    This class implements methods for the commit/distro/extended dlrn hash
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
        check_hash(self.commit_hash)
        check_hash(self.distro_hash)
        check_extended_hash(self.extended_hash)

    def __repr__(self):
        """
        implements special method to output the hash information
        useful for logging and debugging
        :return: The string representation of the object
        """
        return ("<DlrnCommitDistroExtendedHash object commit: %s,"
                " distro: %s, component: %s, extended: %s, timestamp: %s>"
                "" % (self.commit_hash, self.distro_hash, self.component,
                      self.extended_hash, self.timestamp))

    def __str__(self):
        """
        implements special method to output the hash information
        useful for logging and debugging
        :return: The string representation of the hash informations
        """
        return ("commit: %s, distro: %s, extended: %s, component: %s,"
                "timestamp: %s" % (self.commit_hash, self.distro_hash,
                                   self.extended_hash, self.component,
                                   self.timestamp))

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
                      or self.extended_hash != other.extended_hash
                      or self.component != other.component
                      or self.timestamp != other.timestamp)
        except AttributeError:
            raise TypeError("Cannot compare {} with {}"
                            "".format(type(self), type(other)))

        return result

    def __eq__(self, other):
        """
        Implement special methods of comparison with other object if
        compatible. Raises error if not.
        :param other: The object to compare self to
        :return: bool
        """
        try:
            result = (self.commit_hash == other.commit_hash
                      and self.distro_hash == other.distro_hash
                      and self.extended_hash == other.extended_hash
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
        containing full commit, abbreviated distro and extended hashes
        Work only with single norma dlrn haseh
        :return:  The full hash format or None
        """
        if self.extended_hash is not None:
            ext_distro_hash, ext_commit_hash = self.extended_hash.split('_')
            return '{0}_{1}_{2}_{3}'.format(self.commit_hash,
                                            self.distro_hash[:8],
                                            ext_distro_hash[:8],
                                            ext_commit_hash[:8])
        else:
            return '{0}_{1}'.format(self.commit_hash, self.distro_hash[:8])

    def dump_to_dict(self):
        """
        dumps the hash into a dict
        :return: A dict
        """
        result = dict(
            commit_hash=self.commit_hash,
            distro_hash=self.distro_hash,
            extended_hash=self.extended_hash,
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
        params.extended_hash = self.extended_hash
        params.component = self.component
        params.timestamp = self.timestamp

    @property
    def commit_dir(self):
        """
        Computes the commit path related to the hash in a dlrn repo
        in the format XY/XY/XYZTR
        :return: The computed path
        """
        component_path = ""
        if self.component is not None:
            component_path = "component/{}/".format(self.component)
        commit_dir = "{}{}/{}/{}".format(component_path,
                                         self.commit_hash[:2],
                                         self.commit_hash[2:4],
                                         self.full_hash)
        return commit_dir


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
            raise DlrnHashError("Invalid commit or distro or aggregate hash")
        check_hash(self.commit_hash)
        check_hash(self.distro_hash)
        check_hash(self.aggregate_hash)
        check_extended_hash(self.extended_hash)

    def __repr__(self):
        """
        implements special method to output the hash information
        useful for logging and debugging
        :return: The string representation of the object
        """
        return ("<DlrnAggregateHash object aggregate: %s, commit: %s,"
                " distro: %s, extended: %s, component: %s, timestamp: %s>"
                "" % (self.aggregate_hash, self.commit_hash, self.distro_hash,
                      self.extended_hash, self.component, self.timestamp))

    def __str__(self):
        """
        implements special method to output the hash information
        useful for logging and debugging
        :return: The string representation of the hash informations
        """
        return ("aggregate: %s, commit: %s,"
                " distro: %s, extended: %s, component: %s, timestamp: %s"
                "" % (self.aggregate_hash, self.commit_hash, self.distro_hash,
                      self.extended_hash, self.component, self.timestamp))

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
                      and self.extended_hash == other.extended_hash
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
                      or self.extended_hash != other.extended_hash
                      or self.timestamp != other.timestamp)
        except AttributeError:
            raise TypeError("Cannot compare {} with {}"
                            "".format(type(self), type(other)))

        return result

    @property
    def full_hash(self):
        """
        Property to abstract the common representation of a full dlrn hash
        In aggregate hash the full_hash is the aggregate hash itself
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
            extended_hash=self.extended_hash,
            full_hash=self.full_hash,
            timestamp=self.timestamp,
        )
        return result

    def dump_to_params(self, params):
        """
        Takes a dlrn api params object and dumps the hash information into it
        :param params: The params object to fill
        :return: None
        """
        params.aggregate_hash = self.aggregate_hash
        params.commit_hash = self.commit_hash
        params.distro_hash = self.distro_hash
        params.extended_hash = self.extended_hash
        params.timestamp = self.timestamp

    @property
    def commit_dir(self):
        """
        Computes the commit path related to the hash in a dlrn repo
        in the format XY/XY/XYZTR
        :return: The computed path
        """
        label_string = ""
        if self.label is not None:
            label_string = "{}/".format(self.label)
        commit_dir = "{}{}/{}/{}".format(label_string,
                                         self.aggregate_hash[:2],
                                         self.aggregate_hash[2:4],
                                         self.aggregate_hash)
        return commit_dir


class DlrnHash(object):
    """
    This is the metaclass that creates and returns the instance of
    the class equivalent to the hash type handled. It can return a
    Dlrn hash for the single pipeline or a Dlrn aggregate hash for the
    component pipeline It allows the DlrnHashBase class to be polymorphic,
    and work transparently for the caller as it does not have to worry if
    the hash is for the single or the integration pipelines
    """

    log = logging.getLogger("promoter")

    def __new__(cls, **kwargs):
        """
        Dlrn Hash can be initialized either by direct kwargs value, from a
        dictionary, or from a dlrn api response object
        :param commit: the direct commit hash
        :param distro:  the direct distro hash
        :param extended:  the direct extended hash
        :param aggregate: the direct aggregate_hash
        :param timstamp: the direct timestamp value, must be float
        :param source: A valid dlrn api response object or a dictionary
        that needs to contain *_hash as keys
        :return: The DlrnCommitDistroExtendedHash or DlrnAggregateHash instance
        """
        hash_instance = DlrnCommitDistroExtendedHash(**kwargs)

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
