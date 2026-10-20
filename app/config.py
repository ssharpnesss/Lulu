import os
from pathlib import Path

import toml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr

class ConfigSection(BaseModel):
    model_config = ConfigDict(extra="ignore")

class BotConfig(ConfigSection):
    token: SecretStr
    spam_api_key: SecretStr
    spam_threshold: float = Field(default=0.9, gt=0, le=1)
    protects: list = [
        {"name": "antispam"},
        {"name": "antiflood"},
        {"name": "antiraid"},
        {"name": "welcome"},
        {"name": "captcha"},
    ]

class Config(ConfigSection):
    bot: BotConfig


def parse_config(config_file: str = "config.toml") -> Config:
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env")

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is required")

    path = Path(config_file)
    if not path.is_absolute():
        path = Path.cwd() / path
    if path.suffix != ".toml" and not path.exists():
        path = path.with_suffix(".toml")
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")

    data = toml.loads(path.read_text(encoding="utf-8"))
    data.setdefault("bot", {})["token"] = token
    data.setdefault("bot", {})["spam_api_key"] = os.getenv("SPAM_API_KEY", '-')
    return Config.model_validate(data)
