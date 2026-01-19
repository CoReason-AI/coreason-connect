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
import sys
from unittest import mock

import pytest

from coreason_connect.secrets import EnvSecretsProvider


class TestEnvSecretsProvider:
    @pytest.fixture
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

    # Edge Case Tests

    def test_get_secret_empty_string(self, provider: EnvSecretsProvider) -> None:
        """Test retrieving a secret set to an empty string."""
        with mock.patch.dict(os.environ, {"EMPTY_SECRET": ""}):
            assert provider.get_secret("EMPTY_SECRET") == ""

    def test_get_secret_whitespace(self, provider: EnvSecretsProvider) -> None:
        """Test retrieving a secret containing only whitespace."""
        with mock.patch.dict(os.environ, {"WHITESPACE_SECRET": "   "}):
            assert provider.get_secret("WHITESPACE_SECRET") == "   "

    def test_get_secret_special_chars(self, provider: EnvSecretsProvider) -> None:
        """Test retrieving a secret with special characters."""
        special_val = "!@#$%^&*()_+-=[]{}|;':,./<>?`~\\"
        with mock.patch.dict(os.environ, {"SPECIAL_SECRET": special_val}):
            assert provider.get_secret("SPECIAL_SECRET") == special_val

    def test_get_secret_case_sensitivity(self, provider: EnvSecretsProvider) -> None:
        """
        Test case sensitivity behavior.
        - POSIX (Linux/macOS): Case-sensitive (uppercase != lowercase).
        - Windows: Case-insensitive (uppercase == lowercase).
        """
        with mock.patch.dict(os.environ, {"UPPERCASE_KEY": "value"}, clear=True):
            # Should always find the exact match
            assert provider.get_secret("UPPERCASE_KEY") == "value"

            if sys.platform == "win32":
                # On Windows, lowercase lookup should also work
                assert provider.get_secret("uppercase_key") == "value"
            else:
                # On POSIX, lowercase lookup should fail
                with pytest.raises(KeyError):
                    provider.get_secret("uppercase_key")

    # Complex Scenario Tests

    def test_get_user_credential_json_string(self, provider: EnvSecretsProvider) -> None:
        """
        Test retrieving a complex credential stored as a JSON string.
        The provider should return the raw string as-is without parsing.
        """
        json_val = '{"username": "admin", "password": "super_secret_password!", "meta": {"id": 123}}'
        with mock.patch.dict(os.environ, {"COMPLEX_CRED": json_val}):
            result = provider.get_user_credential("COMPLEX_CRED")
            assert isinstance(result, str)
            assert result == json_val
