import os
from dataclasses import dataclass

import yaml


@dataclass
class MattermostConfig:
    url: str
    api_token: str
    slash_token: str
    webhook_token: str
    listen_channels: list[str] | None  # None = WebSocket listener disabled


@dataclass
class YouTrackConfig:
    url: str
    token: str
    default_project: str


@dataclass
class PathsConfig:
    checklists_dir: str
    projects_config: str


@dataclass
class Config:
    port: int
    base_url: str
    mattermost: MattermostConfig
    youtrack: YouTrackConfig
    paths: PathsConfig


def _parse_channels(value: str) -> list[str] | None:
    channels = [c.strip() for c in value.split(",") if c.strip()]
    return channels if channels else None


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name!r} is not set")
    return value


def load_config(config_path: str) -> Config:
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return Config(
        port=int(os.environ.get("BOT_PORT", 8080)),
        base_url=_require("BOT_BASE_URL").rstrip("/"),
        mattermost=MattermostConfig(
            url=_require("MM_URL").rstrip("/"),
            api_token=_require("MM_API_TOKEN"),
            slash_token=_require("MM_SLASH_TOKEN"),
            webhook_token=os.environ.get("MM_WEBHOOK_TOKEN", ""),
            listen_channels=_parse_channels(os.environ.get("MM_LISTEN_CHANNELS", "")),
        ),
        youtrack=YouTrackConfig(
            url=_require("YT_URL").rstrip("/"),
            token=_require("YT_TOKEN"),
            default_project=os.environ.get("YT_DEFAULT_PROJECT", "HD"),
        ),
        paths=PathsConfig(**data["paths"]),
    )
