import logging
import os
from pathlib import Path

import yaml

from app.core.hashing import hash_api_key
from app.schemas.tool_context import ErpNextTenant

logger = logging.getLogger(__name__)

_keys_index: dict[str, dict] = {}


def load_keys_config(path: str) -> None:
    """Load API keys from a YAML file into the in-memory index."""
    global _keys_index

    p = Path(path)
    if not p.exists():
        logger.warning("Keys config file not found at %s — no API keys loaded", path)
        _keys_index = {}
        return

    with open(p) as f:
        data = yaml.safe_load(f) or {}

    _keys_index = {}
    for entry in data.get("api_keys", []):
        key = entry.get("key", "").strip()
        name = entry.get("name", "").strip()
        if not key or not name:
            logger.warning("Skipping malformed entry in keys config: %s", entry)
            continue

        key_hash = hash_api_key(key)

        tenant = None
        tenant_data = entry.get("tenant")
        if tenant_data:
            tenant = ErpNextTenant(
                url=tenant_data.get("url", ""),
                api_key=tenant_data.get("api_key", ""),
                api_secret=tenant_data.get("api_secret", ""),
            )

        _keys_index[key_hash] = {
            "id": name,
            "name": name,
            "tenant": tenant,
        }

    logger.info("Loaded %d API keys from %s", len(_keys_index), path)


def lookup_key(key_hash: str) -> dict | None:
    """Look up a key by its SHA-256 hash. Returns the key info dict or None."""
    return _keys_index.get(key_hash)


def lookup_tenant(key_id: str) -> ErpNextTenant | None:
    """Find the tenant for a given key ID (name)."""
    for key_info in _keys_index.values():
        if key_info["id"] == key_id:
            return key_info["tenant"]
    return None


def bootstrap_keys_yaml(path: str, initial_keys: str) -> None:
    """Create the YAML file from INITIAL_API_KEYS if it doesn't exist."""
    p = Path(path)
    if p.exists():
        return

    entries = []
    for entry in initial_keys.split(","):
        entry = entry.strip()
        if not entry or ":" not in entry:
            continue
        key, name = entry.split(":", 1)
        entries.append({
            "key": key.strip(),
            "name": name.strip(),
        })

    if not entries:
        return

    p.parent.mkdir(parents=True, exist_ok=True)

    data = {"api_keys": entries}

    # Atomic write: temp file then rename
    tmp = str(p) + ".tmp"
    with open(tmp, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
    os.replace(tmp, str(p))

    logger.info("Bootstrapped %d API keys to %s", len(entries), path)
