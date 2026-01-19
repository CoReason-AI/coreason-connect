# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_connect

import importlib.util
import inspect
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from coreason_connect.config import AppConfig, PluginConfig
from coreason_connect.interfaces import ConnectorProtocol, SecretsProvider
from coreason_connect.utils.logger import logger


@contextmanager
def temporary_sys_path(path: str) -> Generator[None, None, None]:
    """Temporarily add a path to sys.path.

    Args:
        path: The path to add to sys.path.

    Yields:
        None: Yields control back to the caller.
    """
    sys.path.insert(0, path)
    try:
        yield
    finally:
        if path in sys.path:
            sys.path.remove(path)


class PluginLoader:
    """Handles dynamic loading of plugins."""

    def __init__(self, config: AppConfig, secrets: SecretsProvider) -> None:
        """Initialize the PluginLoader.

        Args:
            config: The application configuration.
            secrets: The secrets provider for injecting into plugins.
        """
        self.config = config
        self.secrets = secrets
        self.plugins: dict[str, ConnectorProtocol] = {}

    def load_all(self) -> dict[str, ConnectorProtocol]:
        """Load all configured plugins.

        Returns:
            dict[str, ConnectorProtocol]: A dictionary mapping plugin IDs to their
            ConnectorProtocol implementation instances.
        """
        for plugin_conf in self.config.plugins:
            try:
                if plugin_conf.type == "local_python":
                    connector = self._load_local_python(plugin_conf)
                    if connector:
                        self.plugins[plugin_conf.id] = connector
                        logger.info(f"Loaded plugin: {plugin_conf.id}")
                elif plugin_conf.type == "native":
                    connector = self._load_native(plugin_conf)
                    if connector:
                        self.plugins[plugin_conf.id] = connector
                        logger.info(f"Loaded native plugin: {plugin_conf.id}")
                else:
                    logger.warning(f"Unsupported plugin type '{plugin_conf.type}' for plugin '{plugin_conf.id}'")
            except Exception as e:
                logger.error(f"Failed to load plugin '{plugin_conf.id}': {e}")
                # We continue loading other plugins instead of crashing

        return self.plugins

    def _load_native(self, config: PluginConfig) -> ConnectorProtocol:
        """Load a built-in native plugin.

        Args:
            config: The configuration for the plugin.

        Returns:
            ConnectorProtocol: An instance of the plugin's ConnectorProtocol implementation.

        Raises:
            ImportError: If the plugin module cannot be found.
            ValueError: If the module does not contain a ConnectorProtocol implementation.
        """
        # Normalize the ID to a valid python module name (e.g., "ms365" -> "ms365", "my-plugin" -> "my_plugin")
        module_name = config.id.replace("-", "_")
        full_module_name = f"coreason_connect.plugins.{module_name}"

        try:
            module = importlib.import_module(full_module_name)
        except ImportError as e:
            raise ImportError(f"Native plugin module '{full_module_name}' not found: {e}") from e

        # Find the ConnectorProtocol implementation
        connector_class = None
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, ConnectorProtocol) and obj is not ConnectorProtocol:
                connector_class = obj
                break

        if connector_class is None:
            raise ValueError(f"No ConnectorProtocol implementation found in {full_module_name}")

        return connector_class(self.secrets)

    def _load_local_python(self, config: PluginConfig) -> ConnectorProtocol:
        """Load a local Python plugin from disk.

        Args:
            config: The configuration for the plugin.

        Returns:
            ConnectorProtocol: An instance of the plugin's ConnectorProtocol implementation.

        Raises:
            ValueError: If the plugin configuration is invalid or the path is unsafe.
            FileNotFoundError: If the plugin file does not exist.
            ImportError: If the plugin module cannot be loaded.
        """
        if not config.path:
            raise ValueError(f"Plugin '{config.id}' is missing 'path'")

        safe_zone = Path(os.getcwd()).resolve()
        path_obj = Path(config.path).resolve()

        if not path_obj.is_relative_to(safe_zone):
            raise ValueError(f"Plugin path must be within the safe zone ({safe_zone})")

        if not path_obj.exists():
            raise FileNotFoundError(f"Plugin file not found: {path_obj}")

        module_name = f"plugin_{config.id.replace('-', '_')}"

        # Determine the library root for sibling imports
        # structure: .../local_libs/adapters/adapter.py -> root: .../local_libs
        lib_root = path_obj.parent.parent

        spec = importlib.util.spec_from_file_location(module_name, path_obj)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not create module spec from {path_obj}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module

        try:
            with temporary_sys_path(str(lib_root)):
                spec.loader.exec_module(module)
        except Exception as e:
            # Clean up if execution fails
            if module_name in sys.modules:
                del sys.modules[module_name]
            raise ImportError(f"Error executing module '{module_name}': {e}") from e

        # Find the ConnectorProtocol implementation
        connector_class = None
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            # Check if it implements ConnectorProtocol but is not the abstract base class itself
            if issubclass(obj, ConnectorProtocol) and obj is not ConnectorProtocol:
                connector_class = obj
                break

        if connector_class is None:
            raise ValueError(f"No ConnectorProtocol implementation found in {config.path}")

        # Instantiate
        return connector_class(self.secrets)
