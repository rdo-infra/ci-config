"""
Generic artifact promotion classes
"""
import logging
import os

import paramiko


class PromoterError(Exception):
    """Generic error raised at artifact promoter operations."""

    def __init__(self, details=None):
        if not details:
            details = "unexpected error"
        error_msg = ("Artifact promotion error: %s" % details)
        super(PromoterError, self).__init__(error_msg)


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


class FileArtifactPromoter:
    """
    This class interacts with an remote server to promote generic artifacts.
    """
    log = logging.getLogger("artifact_promoter")

    def __init__(self, client, working_dir):
        """Instantiate a new artifact promoter.

        :param client: sftp client to be used for file operations
        :param working_dir: working directory to perform file operations
        """
        self.working_dir = os.path.expanduser(os.path.expandvars(working_dir))
        self.supported_promotions = []
        # Set sftp client
        self.client = client

    def validate(self, target_label, candidate_label=None):
        """Validates if the requested label promotion is supported.

        :param target_label: target label of a promotion
        :param candidate_label: candidate label of a promotion.
        :return: True if the promotion is supported, False otherwise.
        """
        if not self.supported_promotions:
            # No restrictions means any promotion is supported.
            return True

        for prom in self.supported_promotions:
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

    def get_promotion_content(self, target_label, candidate_label=None):
        """Returns promotion file name and content based on provided labels.

        :param target_label: target label of a promotion.
        :param candidate_label: candidate label for promotion.
        :returns: file name and file content
        """
        raise NotImplementedError

    def promote(self,
                target_label,
                candidate_label=None,
                artifact_name=None,
                artifact_content=None):
        """Promote an artifact to target label.

        This method promotes an artifact (file). It creates a new file in the
          destination server and links to a target label.

        :param target_label: target label of a promotion.
        :param candidate_label: candidate label for promotion. Useful for
          classes that need to retrieve promotion content.
        :param artifact_name: artifact name (file) to be created in the
          destination server.
        :param artifact_content: optional content to be written in the
          artifact (file).
        :return: None
        """
        if not self.validate(target_label, candidate_label=candidate_label):
            msg = "The provided promotion labels are not valid."
            raise PromoterError(details=msg)

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
            raise PromoterError(details=msg)

        try:
            if artifact_name is None:
                # NOTE: artifact_content is optional
                artifact_name, artifact_content = self.get_promotion_content(
                    target_label, candidate_label=candidate_label)
            # Promote label by creating a new file and updating target label
            self.promote_file_artifact(target_label, artifact_name,
                                       file_content=artifact_content)
        except PromoterError:
            msg = ("Failed to promote %s to %s", candidate_label, target_label)
            self.log.error(msg)
            self.client.close()
            raise
        except Exception:
            msg = ("Unexpected error occurred while promoting %s to %s",
                   candidate_label, target_label)
            self.log.error(msg)
            self.client.close()
            raise

        self.log.info("Successfully promoted %s to %s.", candidate_label,
                      target_label)

        # close connection
        self.client.close()

    def promote_file_artifact(
            self, target_label, file_name, file_content=None):
        """Promotes a file artifact with an optional content.

        :param target_label: target label of a promotion.
        :param file_name: name of the file to be created.
        :param file_content: content to be written in the new file.
        :return: None
        """
        existing_server_file = None
        try:
            existing_server_file = self.client.stat(file_name)
        except FileNotFoundError:
            # Continue and create a new compose file in the remote server
            self.log.debug("The expected promotion file doesn't exists in the "
                           "remote server.")
        except Exception:
            msg = ("An exception occurred while searching for target file "
                   "in the remove server. Promotion failed.")
            self.log.error(msg)
            raise PromoterError(details=msg)

        rollback_files = []
        if not existing_server_file:
            # create a new file to represent the latest compose
            try:
                new_file = self.client.file(file_name, mode="w")
                # mark file to be deleted in a rollback action
                rollback_files.append(file_name)
                if file_content:
                    new_file.write(file_content.encode('utf-8'))
                self.log.debug("%s file was successfully created in the "
                               "remote server.", file_name)
                new_file.close()
            except EnvironmentError as ex:
                self.log.exception(ex)
                msg = ("Unable to create a new file artifact in the "
                       "remote server. Artifact promotion failed.")
                self.log.error(msg)
                self.rollback(remove_files=rollback_files)
                raise PromoterError(details=msg)

        previous_file_name = None
        try:
            previous_file_name = self.client.readlink(target_label)
            self.log.debug("Checking target label link: %s", target_label)
        except EnvironmentError:
            self.log.debug("No link named %s exists. Will attempt to create a "
                           "new one.", target_label)

        # Unlink if exists and different from expected
        rollback_previous_links = {}
        if previous_file_name:
            if previous_file_name == file_name:
                self.log.debug("The target label already points to the "
                               "latest compose id.")
                return

            rollback_previous_links[target_label] = previous_file_name
            try:
                self.client.unlink(target_label)
                self.log.debug("Removing label link for %s", target_label)
            except EnvironmentError:
                msg = ("Unable to unlink the current target_label: %s" %
                       target_label)
                self.log.error(msg)
                self.rollback(remove_files=rollback_files)
                raise PromoterError(details=msg)

        try:
            self.client.symlink(file_name, target_label)
            self.log.debug("Created symlink: %s -> %s",
                           target_label, file_name)
        except EnvironmentError:
            msg = ("Failed to link %(dest)s to %(src)s" % {
                'dest': target_label,
                'src': file_name
            })
            self.log.error(msg)
            self.rollback(remove_files=rollback_files,
                          previous_links=rollback_previous_links)
            raise PromoterError(details=msg)
