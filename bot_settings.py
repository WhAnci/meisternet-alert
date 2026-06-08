import json
import os
from datetime import datetime
from typing import Any, Dict, Optional


SETTINGS_FILE = os.getenv("BOT_SETTINGS_FILE", "bot_settings.json")
LOG_FILE = os.getenv("BOT_LOG_FILE", "bot_events.log")


def load_settings() -> Dict[str, Any]:
    if not os.path.exists(SETTINGS_FILE):
        return {}

    with open(SETTINGS_FILE, encoding="utf-8") as file:
        return json.load(file)


def save_settings(settings: Dict[str, Any]) -> None:
    with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(settings, file, ensure_ascii=False, indent=2)


def get_alert_channel_id() -> Optional[str]:
    env_channel_id = os.getenv("SLACK_CHANNEL_ID")
    if env_channel_id:
        return env_channel_id

    settings = load_settings()
    channel_id = settings.get("alert_channel_id") or settings.get("discord_channel_id")
    return str(channel_id) if channel_id else None


def get_alert_mention() -> Optional[str]:
    env_mention = os.getenv("SLACK_MENTION")
    if env_mention:
        return env_mention

    settings = load_settings()
    mention = settings.get("alert_mention")
    return str(mention) if mention else None


def set_alert_settings(channel_id: str, mention: Optional[str] = None) -> None:
    settings = load_settings()
    settings["alert_channel_id"] = channel_id
    settings["alert_mention"] = mention
    settings.pop("discord_channel_id", None)
    settings.pop("discord_role_id", None)
    save_settings(settings)


def set_alert_channel_id(channel_id: str) -> None:
    set_alert_settings(channel_id)


def clear_alert_settings() -> None:
    settings = load_settings()
    settings.pop("alert_channel_id", None)
    settings.pop("alert_mention", None)
    settings.pop("discord_channel_id", None)
    settings.pop("discord_role_id", None)
    save_settings(settings)


def append_log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] {message}\n")


def read_recent_logs(limit: int = 10) -> list[str]:
    if not os.path.exists(LOG_FILE):
        return []

    with open(LOG_FILE, encoding="utf-8") as file:
        lines = [line.rstrip("\n") for line in file if line.strip()]
    return lines[-limit:]
