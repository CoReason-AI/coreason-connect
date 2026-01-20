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
from pathlib import Path
from typing import Annotated, Any

import yaml
from pydantic import BaseModel, BeforeValidator, Field, field_validator

from coreason_connect.utils.logger import logger


def force_str(v: Any) -> str:
    """Force conversion of a value to a string.

    Args:
        v: The value to convert.

    Returns:
        str: The string representation of the value.
    """
    return str(v)


Stringified = Annotated[str, BeforeValidator(force_str)]


class PluginConfig(BaseModel):
    """Configuration for a single plugin.

    Attributes:
        id: Unique identifier for the plugin.
        type: Type of the plugin (e.g., 'local_python', 'openapi', 'native').
        path: Path to the plugin source or spec.
        description: Human-readable description of the plugin.
        env_vars: Environment variables required by the plugin.
        base_url: Base URL for OpenAPI plugins.
        scopes: OAuth scopes for native plugins.
    """

    id: str = Field(..., description="Unique identifier for the plugin")
    type: str = Field(..., description="Type of the plugin (local_python, openapi, native)")
    path: str | None = Field(None, description="Path to the plugin source or spec")
    description: str | None = Field(None, description="Human-readable description")
    env_vars: dict[str, Stringified] = Field(
        default_factory=dict, description="Environment variables required by the plugin"
    )
    base_url: str | None = Field(None, description="Base URL for OpenAPI plugins")
    scopes: list[str] = Field(default_factory=list, description="OAuth scopes for native plugins")

    @field_validator("path")
    @classmethod
    def validate_path_safety(cls, v: str | None) -> str | None:
        """Ensure the plugin path is within the safe execution zone.

        Args:
            v: The path string to validate.

        Returns:
            str | None: The validated path, or None.

        Raises:
            ValueError: If the path is outside the safe zone or invalid.
        """
        if v is None:
            return v

        safe_zone = Path(os.getcwd()).resolve()
        try:
            # resolve() handles '..' and symlinks
            target_path = Path(v).resolve()
        except Exception as e:
            raise ValueError(f"Invalid path resolution: {e}") from e

        if not target_path.is_relative_to(safe_zone):
            raise ValueError(f"Plugin path must be within the safe zone ({safe_zone})")

        return v


class AppConfig(BaseModel):
    """Root configuration for the application.

    Attributes:
        plugins: List of configured plugins.
    """

    plugins: list[PluginConfig] = Field(default_factory=list, description="List of configured plugins")

    @field_validator("plugins")
    @classmethod
    def check_unique_ids(cls, v: list[PluginConfig]) -> list[PluginConfig]:
        """Ensure that all plugin IDs are unique.

        Args:
            v: List of PluginConfig objects.

        Returns:
            list[PluginConfig]: The validated list of plugins.

        Raises:
            ValueError: If duplicate plugin IDs are found.
        """
        ids = [p.id for p in v]
        if len(ids) != len(set(ids)):
            duplicates = set([x for x in ids if ids.count(x) > 1])
            raise ValueError(f"Duplicate plugin IDs found: {duplicates}")
        return v


def load_config(config_path: str | Path | None = None) -> AppConfig:
    """Load the application configuration from a YAML file.

    Args:
        config_path: Path to the configuration file. If None, checks the
            COREASON_CONFIG_PATH environment variable or defaults to
            'connectors.yaml' in the current directory.

    Returns:
        AppConfig: The parsed application configuration.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If the configuration file is invalid or cannot be parsed.
    """
    if config_path is None:
        config_path = os.getenv("COREASON_CONFIG_PATH", "connectors.yaml")

    path_obj = Path(config_path)
    logger.info(f"Loading configuration from {path_obj.absolute()}")

    if not path_obj.exists():
        logger.error(f"Configuration file not found: {path_obj}")
        raise FileNotFoundError(f"Configuration file not found at {path_obj}")

    try:
        with open(path_obj, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML configuration: {e}")
        raise ValueError(f"Invalid YAML configuration: {e}") from e

    if not isinstance(raw_data, dict):
        # Handle empty file or invalid root
        if raw_data is None:
            raw_data = {}
        else:
            logger.error(f"Configuration root must be a dictionary, got {type(raw_data)}")
            raise ValueError("Configuration root must be a dictionary")

    try:
        config = AppConfig(**raw_data)
        logger.info(f"Successfully loaded {len(config.plugins)} plugins")
        return config
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise ValueError(f"Configuration validation failed: {e}") from e
