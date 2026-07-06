"""
Loads configuration from config/config.yaml, with environment variables
(.env) taking precedence for sensitive values like DB credentials.
"""

import os
import yaml
from dotenv import load_dotenv

load_dotenv()  # loads .env into os.environ if present


def load_config(config_path: str = "config/config.yaml") -> dict:
    """
    Load YAML config and overlay DB credentials from environment variables
    when present. Falls back to config/config.yaml.example if config.yaml
    hasn't been created yet, so the project still runs out of the box.
    """
    if not os.path.exists(config_path):
        example_path = config_path + ".example"
        if os.path.exists(example_path):
            config_path = example_path
        else:
            raise FileNotFoundError(
                f"No config file found at {config_path} or {example_path}. "
                "Copy config/config.yaml.example to config/config.yaml and edit it."
            )

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Environment variables override YAML (useful for CI / Docker / secrets)
    db = config.setdefault("database", {})
    db["host"] = os.getenv("DB_HOST", db.get("host", "localhost"))
    db["port"] = int(os.getenv("DB_PORT", db.get("port", 3306)))
    db["user"] = os.getenv("DB_USER", db.get("user", "root"))
    db["password"] = os.getenv("DB_PASSWORD", db.get("password", ""))
    db["database"] = os.getenv("DB_NAME", db.get("database", "sales_reporting_db"))

    return config
