# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

from coreason_connect.types import ConnectorConfig, ConnectorManifest, ToolCapability


def test_tool_capability_creation():
    cap = ToolCapability(
        name="test_tool",
        description="A test tool",
        input_schema={"type": "object"},
        is_consequential=True,
    )
    assert cap.name == "test_tool"
    assert cap.is_consequential is True


def test_connector_config_creation():
    config = ConnectorConfig(
        id="rightfind",
        type="local_python",
        path="./adapters/rf_adapter.py",
        env={"RF_BASE_URL": "https://example.com"},
        capabilities={"is_consequential": ["purchase_article"]},
    )
    assert config.id == "rightfind"
    assert config.env["RF_BASE_URL"] == "https://example.com"


def test_connector_manifest_parsing():
    data = {
        "connectors": [
            {
                "id": "rightfind",
                "type": "local_python",
                "path": "./adapters/rf_adapter.py",
            },
            {
                "id": "confex",
                "type": "openapi",
                "path": "./specs/confex_swagger.json",
                "base_url": "https://confex.com",
            },
        ]
    }
    manifest = ConnectorManifest(**data)
    assert len(manifest.connectors) == 2
    assert manifest.connectors[1].type == "openapi"
