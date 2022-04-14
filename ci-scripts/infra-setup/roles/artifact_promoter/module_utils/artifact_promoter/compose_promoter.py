"""
Compose promoter class
"""
import urllib.request

from .promoter import FileArtifactPromoter, PromoterError


class ComposePromoter(FileArtifactPromoter):
    """
    CentOS compose promoter class.
    """

    def __init__(self, client, working_dir, compose_url=None):
        """Instantiate a new compose promoter.

        :param client: client to be used for file operations
        :param working_dir: working directory to perform file operations
        :param compose_url: url used to fetch latest compose-id for an
          specific distro.
        """
        super(ComposePromoter, self).__init__(client, working_dir)
        self.compose_url = compose_url
        # Current supported promotions for CentOS compose
        self.supported_promotions = [
            {'candidate': 'latest-compose', 'target': 'centos-ci-testing'},
        ]

    def retrieve_latest_compose(self):
        """Retrieves the latest compose from centos url.

        :return: String with the latest compose id.
        """
        try:
            latest_compose_id = urllib.request.urlopen(
                self.compose_url).readline().decode('utf-8')
        except Exception:
            msg = ("Failed to retrieve latest compose from url: %s"
                   % self.compose_url)
            self.log.error(msg)
            raise PromoterError(details=msg)

        self.log.info("Retrieved latest compose-id: %s", latest_compose_id)
        return latest_compose_id

    def get_promotion_content(self, target_label, candidate_label=None):
        """Retrieves promotion file name and content for latest-compose."""
        if candidate_label != 'latest-compose':
            msg = ("Candidate label '%s' not supported." % candidate_label)
            self.log.error(msg)
            raise PromoterError(details=msg)

        latest_compose_id = self.retrieve_latest_compose()
        # File name and content are the compose_id
        return latest_compose_id, latest_compose_id
