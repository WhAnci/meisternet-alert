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


def get_alert_channel_id() -> Optional[int]:
    env_channel_id = os.getenv("DISCORD_CHANNEL_ID")
    if env_channel_id:
        return int(env_channel_id)

    channel_id = load_settings().get("discord_channel_id")
    return int(channel_id) if channel_id else None


def get_alert_role_id() -> Optional[int]:
    env_role_id = os.getenv("DISCORD_ROLE_ID")
    if env_role_id:
        return int(env_role_id)

    role_id = load_settings().get("discord_role_id")
    return int(role_id) if role_id else None


def set_alert_settings(channel_id: int, role_id: Optional[int] = None) -> None:
    settings = load_settings()
    settings["discord_channel_id"] = channel_id
    settings["discord_role_id"] = role_id
    save_settings(settings)


def set_alert_channel_id(channel_id: int) -> None:
    set_alert_settings(channel_id)


def clear_alert_settings() -> None:
    settings = load_settings()
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
