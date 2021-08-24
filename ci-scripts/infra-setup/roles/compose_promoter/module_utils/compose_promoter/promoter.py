"""
Main compose promoter file
"""
import logging
import os
import urllib.request

import paramiko


class ComposePromoterError(Exception):
    """Generic error raised at compose promoter operations."""

    def __init__(self, details=None):
        if not details:
            details = "unexpected error"
        error_msg = ("Compose promoter error: %s" % details)
        super(ComposePromoterError, self).__init__(error_msg)


class SftpClient:
    """Creates a SFTP client connection to perform remote file operations."""

    _DEFAULT_HOSTNAME = "127.0.0.1"
    _DEFAULT_PORT = 22

    def __init__(self, hostname=None, user=None, pkey_path=None,
                 port=None, password=None):
        self._host = hostname or self._DEFAULT_HOSTNAME
        self._user = (
            os.path.expandvars(user) if user else os.environ.get("USER"))
        self._key_path = os.path.expanduser(os.path.expandvars(pkey_path))
        self._port = port or self._DEFAULT_PORT
        self._password = password
        self._key = None

        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.load_system_host_keys()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._sftp_client = None

        # Expand user home dir if needed
        if self._key_path:
            key_path = os.path.expanduser(self._key_path)
            self._key = paramiko.RSAKey.from_private_key_file(
                filename=key_path)

    def connect(self):
        self.ssh_client.connect(self._host,
                                port=self._port,
                                username=self._user,
                                password=self._password,
                                pkey=self._key)

        self._sftp_client = self.ssh_client.open_sftp()

    def __getattr__(self, item):
        return getattr(self._sftp_client, item)

    def close(self):
        self._sftp_client.close()


class ComposePromoter:
    """
    This class interacts with an artifact server to promote centos compose ids.
    """
    log = logging.getLogger("compose_promoter")

    def __init__(self, client, working_dir, distro, compose_url):
        """Instantiate a new compose promoter.

        :param client: client to be used for file operations
        :param working_dir: working directory to perform file operations
        :param distro: distro being used for promotion
        :param compose_url: url used to fetch latest compose-id for an
          specific distro.
        """
        self.distro = distro
        self.working_dir = os.path.expanduser(os.path.expandvars(working_dir))
        self.compose_url = compose_url
        # Set sftp client
        self.client = client

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
            raise ComposePromoterError(details=msg)

        self.log.info("Retrieved latest compose-id: %s", latest_compose_id)
        return latest_compose_id

    def validate(self, target_label, candidate_label=None):
        """Validates if the requested label promotion is supported.

        :param target_label: target label of a promotion
        :param candidate_label: candidate label of a promotion.
        :return: True if the promotion is supported, False otherwise.
        """
        supported_promotions = [
            {'candidate': 'latest-compose', 'target': 'centos-ci-testing'},
        ]
        #  {'candidate': 'centos-ci-testing', 'target': 'current-centos'},
        for prom in supported_promotions:
            if (candidate_label == prom['candidate']
                    and target_label == prom['target']):
                return True
        return False

    def rollback(self, remove_files=None, previous_links=None):
        """ Rollback a failed promotion.

        This rollback should take care of fixing symlinks to the previous
        configuration

        :param remove_files: files that need to be removed in the current dir.
        :param previous_links: dict of file to be restored.
        :return: None
        """
        files = remove_files or []
        for file in files:
            try:
                self.client.remove(file)
            except Exception as ex:
                self.log.debug("Rollback: failed to remove file %s. "
                               "Details: %s", file, str(ex))
                # continue to the next one

        links = previous_links or {}
        for label, file in links.items():
            try:
                self.client.unlink(label)
                self.client.symlink(file, label)
            except Exception as ex:
                self.log.debug("Rollback: failed to rollback to previous link"
                               "%s -> %s. Details: %s", label, file, str(ex))

    def promote(self, target_label, candidate_label="latest-compose"):
        """Promote a compose artifact.

        This method can fetch information about the latest compose from
        previous configured url and update symbolic links.

        :param target_label: target label of a promotion.
        :param candidate_label: candidate label for promotion.
        :return: None
        """
        if not self.validate(target_label, candidate_label=candidate_label):
            msg = "The provided promotion labels are not valid."
            raise ComposePromoterError(details=msg)

        self.client.connect()

        # Sanity checks on destination dir
        try:
            self.client.listdir(self.working_dir)
            # set destination dir as current
            self.client.chdir(self.working_dir)
        except FileNotFoundError:
            msg = ("Artifact destination dir '%s' does not exist "
                   "in the server, or is not accessible" % self.working_dir)
            self.client.close()
            raise ComposePromoterError(details=msg)

        # NOTE(dviroel): this is the only compose promotion available so far.
        #   We'll need to add logic for future promotions.
        try:
            self.promote_latest_compose(target_label)
        except ComposePromoterError:
            msg = ("Failed to promote %s to %s", candidate_label, target_label)
            self.log.error(msg)
            self.client.close()
            raise

        self.log.info("Successfully promoted %s to %s.", candidate_label,
                      target_label)

        # close connection
        self.client.close()

    def promote_latest_compose(self, target_label):
        """Promotes a compose artifact based on centos latest compose id.

        :param target_label: target label of a promotion
        :return: None
        """
        # Retrieve latest compose-id from composes.centos.org
        latest_compose_id = self.retrieve_latest_compose()

        server_compose_file = None
        try:
            server_compose_file = self.client.stat(latest_compose_id)
        except FileNotFoundError:
            # Continue and create a new compose file in the remote server
            self.log.debug("The latest compose file doesn't exists in the "
                           "remote server.")
        except Exception:
            msg = ("An exception occurred while searching for compose "
                   "files in the remove server. Promotion failed.")
            self.log.error(msg)
            raise ComposePromoterError(details=msg)

        rollback_files = []
        if not server_compose_file:
            # create a new file to represent the latest compose
            try:
                new_compose_file = self.client.file(latest_compose_id,
                                                    mode="w")
                # mark file to be deleted in a rollback action
                rollback_files.append(latest_compose_id)
                new_compose_file.write(latest_compose_id.encode('utf-8'))
                self.log.debug("%s file was successfully created in the "
                               "remote server.", latest_compose_id)
                new_compose_file.close()
            except EnvironmentError as ex:
                self.log.exception(ex)
                msg = ("Unable to create a new compose file in the "
                       "remote server. Promotion failed.")
                self.log.error(msg)
                raise ComposePromoterError(details=msg)

        previous_compose = None
        try:
            previous_compose = self.client.readlink(target_label)
            self.log.debug("Checking target label link: %s", target_label)
        except EnvironmentError:
            self.log.debug("No link named %s exists. Will attempt to create a "
                           "new one.", target_label)

        # Unlink if exists and different from expected
        rollback_previous_links = {}
        if previous_compose:
            if previous_compose == latest_compose_id:
                self.log.debug("The target label already points to the "
                               "latest compose id.")
                return

            rollback_previous_links[target_label] = previous_compose
            try:
                self.client.unlink(target_label)
                self.log.debug("Removing label link for %s", target_label)
            except EnvironmentError:
                msg = ("Unable to unlink the current target_label: %s" %
                       target_label)
                self.log.error(msg)
                self.rollback(remove_files=rollback_files)
                raise ComposePromoterError(details=msg)

        try:
            self.client.symlink(latest_compose_id, target_label)
            self.log.debug("Created symlink: %s -> %s",
                           target_label, latest_compose_id)
        except EnvironmentError:
            msg = ("Failed to link %(dest)s to %(src)s" % {
                'dest': target_label,
                'src': latest_compose_id
            })
            self.log.error(msg)
            self.rollback(remove_files=rollback_files,
                          previous_links=rollback_previous_links)
            raise ComposePromoterError(details=msg)
