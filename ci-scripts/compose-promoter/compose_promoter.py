"""
Main compose promoter file
"""
import argparse
import logging
import os
import urllib.request
import sys

import paramiko

import constants as const
import exceptions as exc
import config as cfg


class SftpClient:
    """Creates a SFTP client connection with a host."""

    def __init__(self, config, verbose=False):
        self._host = config.get('server_hostname')
        self._user = config.get('server_user', os.environ.get("USER"))
        self._key_path = config.get('server_private_key_path')
        self._port = config.get('server_port', const.SSH_DEFAULT_PORT)
        self._password = config.get('server_password')
        self._key = None

        if verbose:
            logging.getLogger('paramiko.transport').setLevel(logging.DEBUG)

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
    log = logging.getLogger("compose-promoter")

    def __init__(self, config, verbose=False):
        self.config = config
        self.distro = 'centos8'
        self.dest_dir = config.get('server_destination_dir')
        # TODO(dviroel): adapt for other releases
        self.compose_ulr = config.get(
            'latest_compose_url',
            const.LATEST_COMPOSE_URL % {
                'distro': const.LATEST_CENTOS_8_STREAM}
        )
        # Create sftp client
        self.client = SftpClient(config, verbose)

    def retrieve_latest_compose(self):
        """Retrieves the latest compose from centos url.

        :return: String with the latest compose id.
        """
        try:
            latest_compose_id = urllib.request.urlopen(
                self.compose_ulr).readline().decode('utf-8')
        except Exception as ex:
            # self.log.exception(ex)
            msg = ("Failed to retrieve latest compose from url: %s"
                   % self.compose_ulr)
            self.log.error(msg)
            raise exc.ComposePromoterServerConnError(details=msg)

        self.log.info("Retrieved latest compose-id: %s", latest_compose_id)
        return latest_compose_id

    def validate(self, target_label, candidate_label=None):
        """Validates if the requested label promotion is supported.

        :param target_label: target label of a promotion
        :param candidate_label: candidate label of a promotion.
        :return: True if the promotion is supported, False otherwise.
        """
        supported_promotions = [
            {'candidate': None, 'target': 'tripleo-ci-testing'},
        ]
        # TODO(dviroel): next promotion to be added:
        #  {'candidate': 'tripleo-ci-testing', 'target': 'current-tripleo'},
        for prom in supported_promotions:
            if (candidate_label == prom['candidate']
                    and target_label == prom['target']):
                return True
        return False

    def rollback(self):
        """ Rollback a failed promotion.

        This rollback should take care of fixing symlinks to the previous
        configuration

        :return: None
        """
        pass

    def promote(self, target_label, candidate_label=None,
                create_previous=True):
        """Promote a compose artifact.

        This method can fetch information about the latest compose from
        previous configured url and update symbolic links.

        :param target_label: target label of a promotion.
        :param candidate_label: candidate label for promotion.
        :param create_previous: set to True when previous tag must be created.
        :return: None
        """
        self.client.connect()

        if not self.validate(target_label, candidate_label=candidate_label):
            msg = "The provided promotion labels aren't not valid."
            raise exc.ComposePromoterNotSupported(details=msg)

        # Sanity checks on destination dir
        try:
            self.client.listdir(self.dest_dir)
            # set destination dir as current
            self.client.chdir(self.dest_dir)
        except FileNotFoundError as ex:
            msg = ("Artifact destination dir '%s' does not exist "
                   "in the server, or is not accessible" % self.dest_dir)
            self.client.close()
            raise exc.ComposePromoterOperationError('listdir', details=msg)

        # NOTE(dviroel): the only compose promotion available so far.
        try:
            self.promote_latest_compose(target_label)
        except Exception:
            self.log.error("Failed to promote %s to %s",
                           candidate_label or 'latest_compose_id',
                           target_label)
            self.client.close()
            raise

        self.log.debug("Successfully promoted %s to %s.",
                       candidate_label or 'latest_compose_id',
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
            self.log.error("An exception occurred while searching for compose "
                           "files in the remove server. Promotion failed.")
            raise

        if not server_compose_file:
            # create a new file to represent the latest compose
            try:
                new_compose_file = self.client.file(latest_compose_id,
                                                    mode="w")
                new_compose_file.write(latest_compose_id.encode('utf-8'))
                self.log.debug("%s file was successfully created in the "
                               "remote server.", latest_compose_id)
                new_compose_file.close()
            except EnvironmentError as ex:
                self.log.exception(ex)
                msg = ("Unable to create a new compose file in the "
                       "remote server. Promotion failed.")
                self.log.error(msg)
                raise exc.ComposePromoterOperationError('file',
                                                        details=msg)

        current_compose = None
        try:
            current_compose = self.client.readlink(target_label)
            self.log.debug("Checking target label link: %s", target_label)
        except EnvironmentError:
            self.log.debug("No link named %s exists. Will attempt to create a "
                           "new one.", target_label)
            # TODO self.rollback()

        # Unlink if exists and different from expected
        if current_compose:
            if current_compose == latest_compose_id:
                self.log.debug("The target label already points to the "
                               "latest compose id.")
                return

            try:
                self.client.unlink(target_label)
                self.log.debug("Removing label link for %s", target_label)
            except EnvironmentError:
                msg = ("Unable to unlink the current target_label: %s",
                       target_label)
                self.log.error(msg)
                raise exc.ComposePromoterOperationError('unlink',
                                                        details=msg)
                # TODO self.rollback()

        try:
            self.client.symlink(latest_compose_id, target_label)
            self.log.debug("Created symlink: %s -> %s",
                           target_label, latest_compose_id)
        except EnvironmentError:
            msg = ("Failed to link %s to %s", target_label, latest_compose_id)
            self.log.error(msg)
            raise exc.ComposePromoterOperationError('unlink',
                                                    details=msg)
            # TODO self.rollback()


def parse_args():
    # Main parser
    main_parser = argparse.ArgumentParser()
    main_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        default=False,
        help='enable verbose log level for debugging',
    )
    main_parser.add_argument(
        '--config', '-c',
        dest='config_file',
        help='sets file path of a configuration file'
    )

    subparsers = main_parser.add_subparsers(dest='command')

    # Subcommands
    subparsers.add_parser(
        'latest-compose',
        help='promote latest compose-id to "tripleo-ci-testing"'
    )

    args = main_parser.parse_args()
    if args.command is None:
        main_parser.print_help()
        sys.exit(2)

    if args.verbose:
        log = logging.getLogger('compose-promoter')
        log.setLevel(logging.DEBUG)
        log.debug('Logging level set to DEBUG')

    if args.command == 'latest-compose':
        compose_config = cfg.ComposeConfig(args.config_file)
        config = compose_config.load()

        promoter = ComposePromoter(config, verbose=args.verbose)
        promoter.promote('tripleo-ci-testing')


def main():
    logging.basicConfig()
    log = logging.getLogger('compose-promoter')
    log.setLevel(logging.INFO)

    try:
        parse_args()
        sys.exit(0)
    except KeyboardInterrupt:
        log.info("Exiting on user interrupt")
        sys.exit(2)
    except Exception as e:
        log.error(str(e))
        sys.exit(2)


if __name__ == '__main__':
    main()
