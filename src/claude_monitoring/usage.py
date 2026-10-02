"""Credentials, usage fetching and formatting helpers. No GTK here."""

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple

USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
DEFAULT_CREDENTIALS = "~/.claude/.credentials.json"
USER_AGENT = "claude-monitoring"
TIMEOUT = 10


class UsageError(Exception):
    """Base class for usage errors."""


class NoCredentials(UsageError):
    pass


class TokenExpired(UsageError):
    pass


class BadCredentials(UsageError):
    pass


class AuthError(UsageError):
    pass


class RateLimited(UsageError):
    pass


class Offline(UsageError):
    pass


def needs_login(exc) -> bool:
    return isinstance(exc, (NoCredentials, TokenExpired, AuthError, BadCredentials))


def load_token(path=None, now=None) -> str:
    path = path or os.environ.get("CLAUDE_USAGE_CREDENTIALS") or DEFAULT_CREDENTIALS
    path = os.path.expanduser(path)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        raise NoCredentials("credentials file not found")
    except (OSError, ValueError):
        raise BadCredentials("credentials file unreadable")
    oauth = data.get("claudeAiOauth") if isinstance(data, dict) else None
    token = oauth.get("accessToken") if isinstance(oauth, dict) else None
    if not token or not isinstance(token, str):
        raise NoCredentials("no access token in credentials")
    expires = oauth.get("expiresAt")
    if isinstance(expires, (int, float)):
        now_ms = (now if now is not None else datetime.now(timezone.utc).timestamp()) * 1000
        if expires <= now_ms:
            raise TokenExpired("access token expired")
    return token


@dataclass
class UsageWindow:
    percent: Optional[float] = None
    resets_at: Optional[datetime] = None


@dataclass
class Usage:
    five_hour: UsageWindow
    weekly: UsageWindow


def fetch_usage(token, opener=urllib.request.urlopen) -> dict:
    req = urllib.request.Request(
        USAGE_URL,
        headers={
            "Authorization": "Bearer " + token,
            "anthropic-beta": "oauth-2025-04-20",
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    try:
        with opener(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise AuthError("unauthorized")
        if e.code == 429:
            raise RateLimited("rate limited")
        raise Offline("HTTP %s" % e.code)
    except (urllib.error.URLError, OSError, TimeoutError):
        raise Offline("network error")
    except ValueError:
        raise Offline("bad response")


def _parse_time(value) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _parse_window(obj) -> UsageWindow:
    if not isinstance(obj, dict):
        return UsageWindow()
    pct = obj.get("utilization")
    if isinstance(pct, bool) or not isinstance(pct, (int, float)):
        pct = None
    return UsageWindow(pct, _parse_time(obj.get("resets_at")))


def parse_usage(data) -> Usage:
    if not isinstance(data, dict):
        data = {}
    return Usage(_parse_window(data.get("five_hour")), _parse_window(data.get("seven_day")))


def format_reset(resets_at, now=None) -> str:
    now = now or datetime.now(timezone.utc)
    secs = int((resets_at - now).total_seconds())
    if secs <= 0:
        return "now"
    mins = secs // 60
    days, rem = divmod(mins, 1440)
    hours, m = divmod(rem, 60)
    if days:
        return "%dd %dh" % (days, hours)
    if hours:
        return "%dh %dm" % (hours, m)
    return "%dm" % m


def severity(percent) -> str:
    if percent is None:
        return "unknown"
    if percent >= 90:
        return "crit"
    if percent >= 70:
        return "warn"
    return "ok"


STATUS = {"ok": "On track", "warn": "Running high", "crit": "Almost out", "unknown": "No data"}


def reset_at(resets_at, now) -> str:
    """'today 16:42' or 'Mon 09:00' in local time."""
    local = resets_at.astimezone()
    if local.date() == now.astimezone().date():
        return local.strftime("today %H:%M")
    return local.strftime("%a %H:%M")


def menu_lines(title, window, now=None) -> Tuple[str, str]:
    """Two menu rows for one window, worded like the usage window."""
    now = now or datetime.now(timezone.utc)
    sev = severity(window.percent)
    if sev == "unknown":
        return "%s   n/a" % title, ""
    line1 = "%s   %d%%  ·  %s" % (title, int(window.percent + 0.5), STATUS[sev])
    line2 = ""
    if window.resets_at is not None:
        line2 = "Resets in %s  ·  %s" % (format_reset(window.resets_at, now),
                                         reset_at(window.resets_at, now))
    return line1, line2
