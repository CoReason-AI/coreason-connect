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
from unittest import mock

import pytest

from coreason_connect.secrets import EnvSecretsProvider


class TestEnvSecretsProvider:
    @pytest.fixture  # type: ignore[misc]
    def provider(self) -> EnvSecretsProvider:
        return EnvSecretsProvider()

    def test_get_secret_exists(self, provider: EnvSecretsProvider) -> None:
        """Test retrieving an existing secret."""
        with mock.patch.dict(os.environ, {"TEST_SECRET": "secret_value"}):
            assert provider.get_secret("TEST_SECRET") == "secret_value"

    def test_get_secret_missing(self, provider: EnvSecretsProvider) -> None:
        """Test retrieving a missing secret raises KeyError."""
        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(KeyError, match="Secret 'MISSING_SECRET' not found"):
                provider.get_secret("MISSING_SECRET")

    def test_get_user_credential_exists(self, provider: EnvSecretsProvider) -> None:
        """Test retrieving an existing user credential."""
        with mock.patch.dict(os.environ, {"TEST_CRED": "cred_value"}):
            assert provider.get_user_credential("TEST_CRED") == "cred_value"

    def test_get_user_credential_missing(self, provider: EnvSecretsProvider) -> None:
        """Test retrieving a missing user credential raises KeyError."""
        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(KeyError, match="Credential 'MISSING_CRED' not found"):
                provider.get_user_credential("MISSING_CRED")
