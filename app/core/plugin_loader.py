import importlib
import logging
from pathlib import Path

import yaml

from app.core.registry import ToolRegistry

logger = logging.getLogger(__name__)


def load_plugins(registry: ToolRegistry, plugins_config_path: Path) -> None:
    if not plugins_config_path.exists():
        logger.warning("Plugins config not found at %s, no tools loaded", plugins_config_path)
        return

    with open(plugins_config_path) as f:
        config = yaml.safe_load(f) or {}

    plugins = config.get("plugins", {})
    for name, cfg in plugins.items():
        if not cfg.get("enabled", False):
            logger.info("Plugin '%s' is disabled, skipping", name)
            continue

        try:
            module = importlib.import_module(f"app.plugins.{name}")
        except ImportError as e:
            logger.error("Failed to import plugin '%s': %s", name, e)
            continue

        register_fn = getattr(module, "register", None)
        if register_fn is None:
            logger.error("Plugin '%s' has no register() function, skipping", name)
            continue

        try:
            register_fn(registry)
            logger.info("Plugin '%s' loaded successfully", name)
        except Exception as e:
            logger.error("Plugin '%s' register() failed: %s", name, e)
