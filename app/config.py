import os
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    initial_api_keys: str = ""
    database_path: str = "data/ph-agent.db"

    model_config = {"env_prefix": "", "case_sensitive": False}


def load_yaml_config(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def get_settings() -> Settings:
    settings = Settings()

    config_dir = Path(os.environ.get("CONFIG_DIR", Path(__file__).parent.parent / "config"))
    yaml_config = load_yaml_config(config_dir / "config.yaml")

    app_conf = yaml_config.get("app", {})
    if "host" in app_conf:
        settings.app_host = app_conf["host"]
    if "port" in app_conf:
        settings.app_port = app_conf["port"]
    if "log_level" in app_conf:
        settings.log_level = app_conf["log_level"]
    if "database_path" in app_conf:
        settings.database_path = app_conf["database_path"]

    return settings
