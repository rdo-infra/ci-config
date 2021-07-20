"""
Compose promote configuration file
"""
import logging
import os
import yaml

import constants as const


class ComposeConfig:
    _log = logging.getLogger("compose-promoter")

    def __init__(self, config_path=None):
        self.config_path = config_path
        self.config = None

    def load(self):
        """Load local config from disk from expected locations."""
        if self.config_path is None:
            file_paths = [
                # pip install --user
                os.path.expanduser(
                    "~/.local/etc/compose-promoter/config.yaml"),
                # root install
                "/etc/compose-promoter/config.yaml",
                # embedded config.yaml as fallback
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "config.yaml")
            ]
            # Search for a configuration file if user didn't pass one
            for file_path in file_paths:
                if os.path.isfile(file_path) and os.access(file_path, os.R_OK):
                    self.config_path = file_path
                    break

        if self.config_path is None:
            # TODO(dviroel): add new exception
            raise

        self._log.info("Using %s as configuration file", self.config_path)

        with open(self.config_path, 'r') as file:
            self.config = yaml.safe_load(file)
            if not all(key in self.config for key in const.CONFIG_KEYS):
                raise
            return self.config

