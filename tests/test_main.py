# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

import asyncio
from unittest.mock import patch

import pytest

from coreason_connect.main import hello_world, main


@pytest.mark.asyncio
async def test_hello_world() -> None:
    """Test that hello_world initializes server and handles cancellation."""
    # Mock AppConfig and CoreasonConnectServiceAsync to avoid side effects
    with (
        patch("coreason_connect.main.AppConfig") as MockConfig,
        patch("coreason_connect.main.CoreasonConnectServiceAsync") as MockServer,
        patch("asyncio.sleep", side_effect=asyncio.CancelledError) as mock_sleep,
    ):
        mock_server_instance = MockServer.return_value
        mock_server_instance.name = "TestServer"
        mock_server_instance.version = "0.0.0"

        # Setup async context manager mock
        mock_server_instance.__aenter__.return_value = mock_server_instance
        mock_server_instance.__aexit__.return_value = None

        # Run hello_world, which should catch CancelledError and exit
        await hello_world()

        # Verification
        MockConfig.assert_called_once()
        MockServer.assert_called_once()
        mock_server_instance.__aenter__.assert_called_once()
        mock_server_instance.__aexit__.assert_called_once()
        mock_sleep.assert_called_once()


def test_main() -> None:
    """Test the main entry point."""
    with patch("coreason_connect.main.asyncio.run") as mock_run:
        main()
        mock_run.assert_called_once()


def test_main_keyboard_interrupt() -> None:
    """Test that main handles KeyboardInterrupt gracefully."""
    with patch("coreason_connect.main.asyncio.run", side_effect=KeyboardInterrupt) as mock_run:
        # Should not raise exception
        main()
        mock_run.assert_called_once()
