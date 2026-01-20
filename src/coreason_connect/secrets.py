# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

import os
from typing import Any

from coreason_connect.interfaces import SecretsProvider


class EnvSecretsProvider(SecretsProvider):
    """A basic secrets provider that retrieves secrets from environment variables.

    This implementation is primarily intended for development and testing
    environments where secrets are injected via the environment.
    """

    def get_secret(self, key: str) -> str:
        """Retrieve a simple secret by key from environment variables.

        Args:
            key: The name of the environment variable.

        Returns:
            str: The value of the environment variable.

        Raises:
            KeyError: If the environment variable is not set.
        """
        if key not in os.environ:
            raise KeyError(f"Secret '{key}' not found in environment variables.")
        return os.environ[key]

    def get_user_credential(self, key: str) -> Any:
        """Retrieve a user credential by key from environment variables.

        For this implementation, it behaves identically to get_secret, assuming
        credentials are stored as simple strings in environment variables.

        Args:
            key: The name of the environment variable.

        Returns:
            Any: The value of the environment variable.

        Raises:
            KeyError: If the environment variable is not set.
        """
        if key not in os.environ:
            raise KeyError(f"Credential '{key}' not found in environment variables.")
        return os.environ[key]
