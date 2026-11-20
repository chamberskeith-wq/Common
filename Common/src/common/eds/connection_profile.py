"""
Created on Nov 20, 2026

@author: keith.chambers

EDS connection profile.

Defines the connection settings used to communicate
with an AVEVA Edge Data Store instance.
"""

from dataclasses import dataclass
from urllib.parse import urlsplit
import logging

from common.configuration import ConfigValidationError


logger = logging.getLogger("common.eds")


# ============================================================
# EDS connection defaults
# ============================================================

DEFAULT_EDS_PORT = 5590
DEFAULT_EDS_URL = "http://localhost"
DEFAULT_EDS_TIMEOUT = 30
DEFAULT_EDS_RETRY_INTERVAL = 5


@dataclass
class EDSConnectionProfile:
    """
    Connection settings for an EDS instance.

    Persistence is handled by the consuming application
    through Common's ConfigManager.

    Credentials are deliberately excluded and should be
    handled separately by Common's SecretManager.
    """

    url: str = DEFAULT_EDS_URL
    port: int = DEFAULT_EDS_PORT
    timeout: int = DEFAULT_EDS_TIMEOUT
    retry_interval: int = DEFAULT_EDS_RETRY_INTERVAL

    def validate(self) -> None:
        """
        Validate the EDS connection settings.

        Raises:
            ConfigValidationError: If a setting is invalid.
        """

        # URL
        if not isinstance(self.url, str) or not self.url.strip():
            raise ConfigValidationError(
                "A valid EDS URL must be provided."
            )

        parsed_url = urlsplit(self.url.strip())

        if (
            parsed_url.scheme not in ("http", "https")
            or not parsed_url.hostname
            or parsed_url.path not in ("", "/")
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise ConfigValidationError(
                "EDS URL must be a valid HTTP or HTTPS base URL "
                "without a path, query or fragment."
            )

        # PORT
        if (
            not isinstance(self.port, int)
            or isinstance(self.port, bool)
            or not 1 <= self.port <= 65535
        ):
            raise ConfigValidationError(
                "Port must be an integer between 1 and 65535."
            )

        # TIMEOUT
        if (
            not isinstance(self.timeout, int)
            or isinstance(self.timeout, bool)
            or self.timeout <= 0
        ):
            raise ConfigValidationError(
                "Timeout must be a positive integer."
            )

        # RETRY INTERVAL
        if (
            not isinstance(self.retry_interval, int)
            or isinstance(self.retry_interval, bool)
            or self.retry_interval <= 0
        ):
            raise ConfigValidationError(
                "Retry interval must be a positive integer."
            )
