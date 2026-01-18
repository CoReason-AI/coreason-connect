# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

from typing import Any

from coreason_connect.interfaces import SecretsProvider


class InvalidAdapter:
    """Does not inherit from ConnectorProtocol"""

    def __init__(self, secrets: SecretsProvider):
        pass

    def get_tools(self) -> list[Any]:
        return []

    def execute(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        return "invalid"
