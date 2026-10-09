# SPDX-License-Identifier: GPL-3.0-or-later
"""ntfy.py: configuration, the token at rest, and what a publish looks like on the wire. No real
network: httpx.post is replaced by a fake that records the request."""

from __future__ import annotations

from contextlib import closing

import httpx
import pytest

from bioseasy import db, ntfy


@pytest.fixture
def conn(tmp_path):
    with closing(db.connect(tmp_path / "bioseasy.db")) as c:
        db.migrate(c)
        yield c


class _Recorder:
    def __init__(self, status=200, exc=None):
        self.calls: list[dict] = []
        self.status = status
        self.exc = exc

    def __call__(self, url, *, json, headers, timeout):
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        if self.exc:
            raise self.exc
        return httpx.Response(self.status)


def test_unconfigured_sends_nothing(conn, tmp_path, monkeypatch):
    fake = _Recorder()
    monkeypatch.setattr(ntfy.httpx, "post", fake)
    result = ntfy.send(conn, tmp_path, "t", "b")
    assert not result.ok and fake.calls == []
    assert not ntfy.load(conn).ready


def test_publishes_json_with_title_priority_tags_and_click(conn, tmp_path, monkeypatch):
    fake = _Recorder()
    monkeypatch.setattr(ntfy.httpx, "post", fake)
    ntfy.save(conn, tmp_path, enabled=True, server="https://ntfy.example/", topic="my-backups", token=None)

    result = ntfy.send(conn, tmp_path, "Backup of Anna’s iPhone failed", "body", event="failed", click="https://b/x")

    assert result.ok
    (call,) = fake.calls
    assert call["url"] == "https://ntfy.example/"
    assert call["json"]["topic"] == "my-backups"
    # JSON publishing, not a Title header: a curly apostrophe is not Latin-1.
    assert call["json"]["title"] == "Backup of Anna’s iPhone failed"
    assert call["json"]["priority"] == 4 and call["json"]["tags"] == ["x"]
    assert call["json"]["click"] == "https://b/x"
    assert "Authorization" not in call["headers"]


def test_token_is_encrypted_at_rest_sent_as_bearer_and_kept_on_blank(conn, tmp_path, monkeypatch):
    fake = _Recorder()
    monkeypatch.setattr(ntfy.httpx, "post", fake)
    ntfy.save(conn, tmp_path, enabled=True, server="https://ntfy.example", topic="t", token="tk_secret")
    assert "tk_secret" not in (db.get_setting(conn, "ntfy_token") or "")
    assert ntfy.load(conn).token_set

    ntfy.save(conn, tmp_path, enabled=True, server="https://ntfy.example", topic="t", token=None)
    ntfy.send(conn, tmp_path, "t", "b")
    assert fake.calls[-1]["headers"]["Authorization"] == "Bearer tk_secret"

    ntfy.save(conn, tmp_path, enabled=True, server="https://ntfy.example", topic="t", token=None, clear_token=True)
    assert not ntfy.load(conn).token_set


def test_switched_off_only_sends_a_forced_test(conn, tmp_path, monkeypatch):
    fake = _Recorder()
    monkeypatch.setattr(ntfy.httpx, "post", fake)
    ntfy.save(conn, tmp_path, enabled=False, server="https://ntfy.example", topic="t", token=None)
    assert not ntfy.send(conn, tmp_path, "t", "b").ok
    assert ntfy.send(conn, tmp_path, "t", "b", force=True).ok
    assert len(fake.calls) == 1


@pytest.mark.parametrize(
    ("status", "exc", "fragment"),
    [
        (403, None, "access token"),
        (500, None, "HTTP 500"),
        (200, httpx.ConnectTimeout("slow"), "in time"),
        (200, httpx.ConnectError("nope"), "Could not reach"),
    ],
)
def test_failures_are_results_never_exceptions_and_never_echo_the_token(
    conn, tmp_path, monkeypatch, status, exc, fragment
):
    monkeypatch.setattr(ntfy.httpx, "post", _Recorder(status=status, exc=exc))
    ntfy.save(conn, tmp_path, enabled=True, server="https://ntfy.example", topic="t", token="tk_secret")
    result = ntfy.send(conn, tmp_path, "t", "b")
    assert not result.ok and fragment in result.error and "tk_secret" not in result.error


@pytest.mark.parametrize(
    ("server", "topic", "ok"),
    [
        ("https://ntfy.sh", "abc-DEF_123", True),
        ("http://192.0.2.5:8090", "x", True),
        ("ntfy.sh", "abc", False),
        ("https://ntfy.sh", "has space", False),
        ("https://ntfy.sh", "a" * 65, False),
    ],
)
def test_validate(server, topic, ok):
    assert (ntfy.validate(server, topic) == []) is ok
