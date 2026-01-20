# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

from coreason_connect.types import ToolExecutionError


def test_tool_execution_error_init() -> None:
    """Test initializing ToolExecutionError."""
    err = ToolExecutionError("Something went wrong", retryable=True)
    assert err.message == "Something went wrong"
    assert err.retryable is True
    assert str(err) == "Something went wrong"


def test_tool_execution_error_defaults() -> None:
    """Test default values for ToolExecutionError."""
    err = ToolExecutionError("Error")
    assert err.retryable is False
