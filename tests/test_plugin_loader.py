import yaml

from app.core.plugin_loader import load_plugins
from app.core.registry import ToolRegistry


def test_load_plugins_skips_disabled(tmp_path):
    config_path = tmp_path / "plugins.yaml"
    config_path.write_text(
        yaml.dump({"plugins": {"system": {"enabled": False}, "erpnext": {"enabled": False}}})
    )

    registry = ToolRegistry()
    load_plugins(registry, config_path)
    assert len(registry) == 0


def test_load_plugins_loads_enabled(tmp_path):
    config_path = tmp_path / "plugins.yaml"
    config_path.write_text(yaml.dump({"plugins": {"system": {"enabled": True}}}))

    registry = ToolRegistry()
    load_plugins(registry, config_path)
    assert len(registry) == 3  # ping, system_info, random_number


def test_load_plugins_missing_config(tmp_path):
    config_path = tmp_path / "nonexistent.yaml"
    registry = ToolRegistry()
    load_plugins(registry, config_path)
    assert len(registry) == 0
