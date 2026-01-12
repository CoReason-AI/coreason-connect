# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

from typing import Any, List

from coreason_connect.interfaces import CoreasonAdapter, SecretsProvider
from coreason_connect.types import ToolCapability


class MockSecretsProvider:
    def get(self, key: str) -> str:
        return "secret"


class MockAdapter:
    def __init__(self, secrets_provider: SecretsProvider) -> None:
        self.secrets = secrets_provider

    def get_capabilities(self) -> List[ToolCapability]:
        return []

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        return "result"


def test_secrets_provider_check():
    provider = MockSecretsProvider()
    assert isinstance(provider, SecretsProvider)


def test_adapter_check():
    provider = MockSecretsProvider()
    adapter = MockAdapter(provider)
    assert isinstance(adapter, CoreasonAdapter)
