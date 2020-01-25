"""
This file contains classes and method relative to the interaction with dlrn
server
"""
import dlrnapi_client
import logging

from legacy_promoter import fetch_jobs, promote_link


class DlrnAggregateHash(str):
    """
    This class represents the aggregate hash for the component pipeline
    Not yet implemented
    """
    pass


class DlrnHash(dict):
    """
    This class represent the dlrn hash, It makes it easier to handle, compare
    and visualize dlrn hashes
    """

    log = logging.getLogger("promoter")

    def __init__(self, commit=None, distro=None, from_api=None, from_dict=None):
        self.commit_hash = ""
        self.distro_hash = ""
        if from_api is not None:
            try:
                self.log.debug("Using values from a Promotion object")
                self.commit_hash = from_api.commit_hash
                self.distro_hash = from_api.distro_hash
            except AttributeError:
                raise AttributeError("Cannot create hash,"
                                     " invalid source API object")
        elif from_dict is not None:
            try:
                self.log.debug("Using values from a Promotion object")
                self.commit_hash = from_dict['commit_hash']
                self.distro_hash = from_dict['distro_hash']
            except KeyError:
                raise KeyError("Cannot create hash:"
                               " invalid source dict")

        else:
            self.commit_hash = commit
            self.distro_hash = distro

    def __eq__(self, other):
        if not hasattr(other, 'commit_hash') or \
           not hasattr(other, 'distro_hash'):
            raise TypeError("One of the objects is not a valid DlrnHash")

        return (self.commit_hash == other.commit_hash
                and self.distro_hash == other.distro_hash)

    def __ne__(self, other):
        if not hasattr(other, 'commit_hash') or \
           not hasattr(other, 'distro_hash'):
            raise TypeError("One of the objects is not a valid DlrnHash")

        return (self.commit_hash != other.commit_hash
                or self.distro_hash != other.distro_hash)

    def __str__(self):
        return "commit: %s, distro: %s" % (self.commit_hash, self.distro_hash)

    def __repr__(self):
        return "<DlrnHash object commit: %s, distro: %s>" % (self.commit_hash,
                                                             self.distro_hash)

    @property
    def full_hash(self):
        """
        Property to abstract the common representation of a full dlrn hash
        containing full commit and distro hashes
        :return:  The full hash format
        """
        return '{0}_{1}'.format(self.commit_hash, self.distro_hash[:8])

    @property
    def short_hash(self):
        """
        Property to abstract the common representation of a full dlrn hash
        containing full commit but abbreviated distro hash
        :return:  The commit and abbreviated distro hash format
        """
        return '{0}_{1}'.format(self.commit_hash[:8], self.distro_hash[:8])

    @property
    def repo_path(self):
        """
        Property to visualize the path to the hash inside dlrn server for the
        single pipeline
        :return:
        """
        url = "{}/{}/{}".format(self.commit_hash[:2],
                                self.commit_hash[2:4],
                                self.full_hash)
        return url


class DlrnClient(object):
    """
    This class represent a wrapper around dlrnapi client operations to perform
    complex operations on hashes
    """

    log = logging.getLogger("promoter")

    def __init__(self, config):
        self.config = config
        # This way of preparing parameters and configuration is copied
        # directly from dlrnapi CLI and ansible module
        self.hashes_params = dlrnapi_client.PromotionQuery()
        self.jobs_params = dlrnapi_client.Params2()
        self.promote_params = dlrnapi_client.Promotion()
        # TODO(gcerami): fix credentials gathering
        dlrnapi_client.configuration.password = self.config.dlrn_password
        dlrnapi_client.configuration.username = self.config.dlrn_username
        api_client = dlrnapi_client.ApiClient(host=self.config.api_url)
        self.api_instance = dlrnapi_client.DefaultApi(api_client=api_client)
        self.log.info('Using API URL: %s', api_client.host)
        self.last_promotions = {}

    def fetch_jobs(self, dlrn_id):
        """
        This method fetch a list of successful jobs from a dlrn server for a
        specific hash identifier.
        :param dlrn_id: The dlrn identifier to fetch jobs from. Currently
        implemented only the commit/distro format. Aggregate hash is not
        implemented
        :return: None
        """
        if self.config.pipeline_type == "single":
            # fetch_job is imported from legacy code
            fetch_jobs(self.api_client, dlrn_id)
        elif self.config.pipeline_type == "component":
            self.log.error("Fetching from aggregate hash is not yet "
                           "implemented")

    def promote_hash(self, dlrn_id, target_label):
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
        if self.config.pipeline_type == "single":
            # promote_link is imported from legacy code
            promote_link(self.api_client, dlrn_id, target_label)
        elif self.config.pipeline_type == "component":
            self.log.error("Component pipeline promotion is not yet "
                           "implemented")

    def get_civotes_info(self, dlrn_id):
        """
        This method assembles information on where to find ci votes for a
        specific dlrn id
        :param dlrn_id: The dlrn identifier to get info for. Currently
        implemented only the commit/distro format. Aggregate hash is not
        implemented
        :return: A string with an url to fetch info from
        """
        if self.config.pipeline_type == "single":
            civotes_info = ('%s \n%s/api/civotes_detail.html?'
                            'commit_hash=%s&distro_hash=%s'.replace(" ", ""),
                            'DETAILED FAILED STATUS: ',
                            self.config.api_url,
                            dlrn_id['commit_hash'],
                            dlrn_id['distro_hash'])
            return civotes_info
        elif self.config.pipeline_type == "component":
            self.log.error("Component pipeline ci votes information is not yet "
                           "available")
