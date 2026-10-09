# SPDX-License-Identifier: GPL-3.0-or-later
"""Alerts through ntfy (https://ntfy.sh, or a self-hosted ntfy server): the only notification path.

One installation-wide target: a server URL, a topic and, for a protected topic, an access token.
Everything lives in the settings table. The token is the one secret; it is encrypted at rest
(secretbox.py) and never rendered back, only whether one is set.

Messages are published as JSON to the server root (https://docs.ntfy.sh/publish/#publish-as-json)
rather than with Title/Tags headers: header values must be Latin-1, and a device called
"Anna’s iPhone" would not survive that.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from . import db, secretbox

log = logging.getLogger("bioseasy")

DEFAULT_SERVER = "https://ntfy.sh"
SEND_TIMEOUT = 15.0

_SERVER_KEY = "ntfy_server"
_TOPIC_KEY = "ntfy_topic"
_TOKEN_KEY = "ntfy_token"  # noqa: S105 - a settings key; the value is Fernet ciphertext
_ENABLED_KEY = "ntfy_enabled"

# ntfy's own topic rule: letters, digits, underscore and dash, up to 64 characters.
_TOPIC_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")

# Per event: ntfy priority (1 min .. 5 max) and tags (emoji shortcodes ntfy renders as icons).
EVENT_STYLE: dict[str, tuple[int, list[str]]] = {
    "succeeded": (3, ["white_check_mark"]),
    "failed": (4, ["x"]),
    "not_confirmed": (3, ["hourglass"]),
    "waiting_for_passcode": (4, ["iphone", "lock"]),
    "upcoming": (3, ["alarm_clock"]),
    "due": (3, ["calendar"]),
    "overdue": (4, ["warning"]),
    "storage_failed": (5, ["rotating_light"]),
    "test": (3, ["bell"]),
}


@dataclass(frozen=True)
class Config:
    enabled: bool
    server: str
    topic: str
    token_set: bool

    @property
    def ready(self) -> bool:
        return self.enabled and bool(self.topic)

    @property
    def subscribe_url(self) -> str:
        return f"{self.server.rstrip('/')}/{self.topic}"


@dataclass(frozen=True)
class Result:
    ok: bool
    error: str = ""


# --- the access token at rest -----------------------------------------------------------------


def _token(conn: sqlite3.Connection, data_dir: Path) -> str | None:
    stored = db.get_setting(conn, _TOKEN_KEY)
    if not stored:
        return None
    try:
        return secretbox.decrypt_secret(data_dir, stored.encode("ascii"))
    except secretbox.SecretError:
        log.warning("ntfy: the stored access token could not be decrypted; sending without it")
        return None


# --- configuration ----------------------------------------------------------------------------


def load(conn: sqlite3.Connection) -> Config:
    return Config(
        enabled=db.get_setting(conn, _ENABLED_KEY, "1") == "1",
        server=db.get_setting(conn, _SERVER_KEY) or DEFAULT_SERVER,
        topic=db.get_setting(conn, _TOPIC_KEY) or "",
        token_set=bool(db.get_setting(conn, _TOKEN_KEY)),
    )


def validate(server: str, topic: str) -> list[str]:
    """Readable problems with a server URL and topic, empty when both are usable."""
    errors = []
    parts = urlsplit(server)
    if parts.scheme not in ("http", "https") or not parts.netloc or parts.query or parts.fragment:
        errors.append("The server must be a web address like https://ntfy.sh.")
    if topic and (len(topic) > 64 or not set(topic) <= _TOPIC_CHARS):
        errors.append("The topic may only use letters, digits, - and _, up to 64 characters.")
    return errors


def save(
    conn: sqlite3.Connection,
    data_dir: Path,
    *,
    enabled: bool,
    server: str,
    topic: str,
    token: str | None,
    clear_token: bool = False,
) -> None:
    """Store the settings. `token` None (a blank field) keeps the stored token; `clear_token`
    removes it."""
    db.set_setting(conn, _ENABLED_KEY, "1" if enabled else "0")
    db.set_setting(conn, _SERVER_KEY, server.rstrip("/"))
    db.set_setting(conn, _TOPIC_KEY, topic)
    if clear_token:
        db.set_setting(conn, _TOKEN_KEY, "")
    elif token:
        db.set_setting(conn, _TOKEN_KEY, secretbox.encrypt_secret(data_dir, token).decode("ascii"))


# --- sending ----------------------------------------------------------------------------------


def send(
    conn: sqlite3.Connection,
    data_dir: Path,
    title: str,
    body: str,
    *,
    event: str = "test",
    click: str | None = None,
    force: bool = False,
) -> Result:
    """Publish one message. Never raises and never takes longer than SEND_TIMEOUT.

    `force` sends even while alerts are switched off (the Send test button). The error text never
    carries the token or the topic, only what went wrong.
    """
    config = load(conn)
    if not config.topic:
        return Result(False, "No ntfy topic is set")
    if not config.enabled and not force:
        return Result(False, "ntfy alerts are switched off")
    priority, tags = EVENT_STYLE.get(event, (3, []))
    payload: dict = {"topic": config.topic, "title": title, "message": body, "priority": priority, "tags": tags}
    if click:
        payload["click"] = click
    headers = {}
    token = _token(conn, data_dir)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = httpx.post(config.server.rstrip("/") + "/", json=payload, headers=headers, timeout=SEND_TIMEOUT)
    except httpx.TimeoutException:
        return Result(False, "The ntfy server did not answer in time")
    except httpx.HTTPError as exc:
        return Result(False, f"Could not reach the ntfy server ({exc.__class__.__name__})")
    if response.status_code in (401, 403):
        return Result(False, "The ntfy server refused the message: check the access token")
    if response.status_code >= 400:
        return Result(False, f"The ntfy server answered HTTP {response.status_code}")
    return Result(True)


def clear_failed_alerts(conn: sqlite3.Connection, udid: str | None = None) -> None:
    """Drop a recorded delivery failure once the ntfy path has been shown to work again.

    devices.last_alert_ok = 0 is otherwise only cleared by the next real alert for that device,
    which can be a day away - and a failure recorded against an earlier notification setup (or an
    earlier release's connectors) keeps warning on the device page long after it stopped being
    true. A successful test, or newly saved settings, is the moment that warning becomes stale.
    """
    if udid is None:
        conn.execute("UPDATE devices SET last_alert_ok = NULL, last_alert_error = NULL WHERE last_alert_ok = 0")
    else:
        conn.execute(
            "UPDATE devices SET last_alert_ok = NULL, last_alert_error = NULL WHERE last_alert_ok = 0 AND udid = ?",
            (udid,),
        )
