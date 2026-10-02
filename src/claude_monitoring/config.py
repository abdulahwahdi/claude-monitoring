"""Small config loader: env vars override ~/.config/claude-monitoring/config.json."""

import json
import os
from dataclasses import dataclass
from typing import Optional

MIN_INTERVAL = 30
DEFAULT_INTERVAL = 120
DEFAULT_LOGIN_COMMAND = "claude auth login"


@dataclass
class Config:
    poll_interval_seconds: int = DEFAULT_INTERVAL
    credentials_path: Optional[str] = None
    login_command: str = DEFAULT_LOGIN_COMMAND


def config_path(env=os.environ):
    """The config file, falling back to the pre-2.0.0 claude-usage-linux one."""
    base = env.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    path = os.path.join(base, "claude-monitoring", "config.json")
    old = os.path.join(base, "claude-usage-linux", "config.json")
    if not os.path.exists(path) and os.path.exists(old):
        return old
    return path


def load_config(path=None, env=os.environ) -> Config:
    data = {}
    try:
        with open(path or config_path(env), "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
        if isinstance(loaded, dict):
            data = loaded
    except (OSError, ValueError):
        pass
    cfg = Config()
    interval = env.get("CLAUDE_USAGE_POLL_INTERVAL", data.get("poll_interval_seconds"))
    try:
        cfg.poll_interval_seconds = max(MIN_INTERVAL, int(interval))
    except (TypeError, ValueError):
        pass
    cfg.credentials_path = env.get("CLAUDE_USAGE_CREDENTIALS") or data.get("credentials_path") or None
    cmd = env.get("CLAUDE_USAGE_LOGIN_COMMAND") or data.get("login_command")
    if isinstance(cmd, str) and cmd.strip():
        cfg.login_command = cmd
    return cfg
