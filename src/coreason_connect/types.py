# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ToolCapability(BaseModel):
    """
    Capability definition for an internal tool.
    """

    name: str
    description: str
    input_schema: Dict[str, Any]  # JSON Schema
    is_consequential: bool = False  # Triggers Human Layer


class ConnectorConfig(BaseModel):
    """
    Configuration for a single connector in the manifest.
    """

    id: str
    type: str  # e.g. "local_python", "openapi"
    path: str
    env: Optional[Dict[str, str]] = None
    base_url: Optional[str] = None
    capabilities: Optional[Dict[str, List[str]]] = None  # e.g. is_consequential: ["purchase_article"]


class ConnectorManifest(BaseModel):
    """
    The manifest file defining all available connectors.
    """

    connectors: List[ConnectorConfig]
