'''
Created on Nov 16, 2026

@author: keith.chambers
'''

"""
Generic application secret manager.

Provides secure storage and retrieval of application secrets
using the operating system credential store.

Environment variables are also supported as an alternative
source of secrets.
"""

import logging
import os
import keyring

from keyring.errors import PasswordDeleteError

from .exceptions import ConfigSecretError


# ============================================================
# Module logger
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# Secret Manager
# ============================================================

class SecretManager:
    """
    Generic secret manager.

    Each application supplies its own service name to keep
    secrets logically separated in the credential store.

    Supports:
        - Store secrets
        - Retrieve secrets
        - Delete secrets
        - Environment variable fallback
    """

    # --------------------------------------------------------
    # Constructor
    # --------------------------------------------------------

    def __init__(self, service_name: str) -> None:

        if not isinstance(service_name, str) or not service_name.strip():
            raise ConfigSecretError(
                "Secret service name must be a non-empty string"
            )

        self.service_name = service_name.strip()

        logger.debug(
            "Secret manager initialized for service: %s",
            self.service_name
        )

    # --------------------------------------------------------
    # Get secret
    # --------------------------------------------------------

    def get_secret(
        self,
        secret_name: str,
        env_var: str | None = None
    ) -> str | None:
        """
        Retrieve a secret.

        Environment variables take precedence over the
        operating system credential store.

        Returns None if the secret is not found.
        """

        self._validate_secret_name(secret_name)

        # Check environment variable first.
        if env_var:

            if not isinstance(env_var, str) or not env_var.strip():
                raise ConfigSecretError(
                    "Environment variable name must be a non-empty string"
                )

            value = os.environ.get(env_var)

            if value:
                return value

        # Check operating system credential store.
        try:
            value = keyring.get_password(
                self.service_name,
                secret_name
            )

            return value or None

        except Exception as e:
            raise ConfigSecretError(
                f"Unable to retrieve secret: {secret_name}"
            ) from e

    # --------------------------------------------------------
    # Set secret
    # --------------------------------------------------------

    def set_secret(
        self,
        secret_name: str,
        value: str
    ) -> None:
        """
        Store a secret in the operating system credential store.

        Secret values are never logged.
        """

        self._validate_secret_name(secret_name)

        if not isinstance(value, str) or not value:
            raise ConfigSecretError(
                "Secret value must be a non-empty string"
            )

        try:
            keyring.set_password(
                self.service_name,
                secret_name,
                value
            )

        except Exception as e:
            raise ConfigSecretError(
                f"Unable to store secret: {secret_name}"
            ) from e

        logger.info(
            "Secret stored successfully: %s",
            secret_name
        )

    # --------------------------------------------------------
    # Delete secret
    # --------------------------------------------------------

    def delete_secret(self, secret_name: str) -> bool:
        """
        Delete a secret from the operating system credential store.

        Returns:
            True if deleted.
            False if the secret did not exist.
        """

        self._validate_secret_name(secret_name)

        try:
            keyring.delete_password(
                self.service_name,
                secret_name
            )

            logger.info("Secret deleted: %s", secret_name)

            return True

        except PasswordDeleteError:
            return False

        except Exception as e:
            raise ConfigSecretError(
                f"Unable to delete secret: {secret_name}"
            ) from e

    # --------------------------------------------------------
    # Internal validation
    # --------------------------------------------------------

    @staticmethod
    def _validate_secret_name(secret_name: str) -> None:

        if not isinstance(secret_name, str) or not secret_name.strip():
            raise ConfigSecretError(
                "Secret name must be a non-empty string"
            )
