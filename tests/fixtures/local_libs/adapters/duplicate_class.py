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

from coreason_connect.interfaces import ConnectorProtocol, SecretsProvider
from coreason_connect.types import ToolDefinition


class ValidAdapter(ConnectorProtocol):
    """
    This class has the same name as the one in valid_adapter.py.
    This tests that the loader handles module isolation correctly.
    """

    def __init__(self, secrets: SecretsProvider):
        super().__init__(secrets)
        self.id = "duplicate"

    def get_tools(self) -> list[ToolDefinition]:
        return []

    def execute(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        return self.id
