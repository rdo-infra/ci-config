"""
This file contains classes and methods to interact with dlrn servers
"""
import dlrnapi_client
import logging

from legacy_promoter import fetch_jobs, promote_link


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
        dlrnapi_client.configuration.password = self.config.dlrnauth_password
        dlrnapi_client.configuration.username = self.config.dlrnauth_username
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
            return fetch_jobs(self.api_instance, dlrn_id)
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
            promote_link(self.api_instance, dlrn_id, target_label)
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
