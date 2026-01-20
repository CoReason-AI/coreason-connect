# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

from mcp.types import Tool
from pydantic import BaseModel


class ToolExecutionError(Exception):
    """Raised when a tool execution fails in a way that should be reported to the LLM.

    Attributes:
        message: The human-readable error message.
        retryable: Whether the error is transient and the operation might succeed if retried.
    """

    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.retryable = retryable

    def __str__(self) -> str:
        return self.message


class ToolDefinition(BaseModel):
    """Internal definition of a tool, including its MCP specification and operational flags.

    Attributes:
        name: The name of the tool (must match tool.name).
        tool: The MCP Tool object.
        is_consequential: If True, requires human approval before execution.
    """

    name: str
    tool: Tool
    is_consequential: bool = False
