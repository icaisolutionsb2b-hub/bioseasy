# SPDX-License-Identifier: GPL-3.0-or-later
"""app.setup_state: once a device has finished the checklist, a backup that is running or one that
failed partway must not put "Setup incomplete" back on its page."""

from __future__ import annotations

from types import SimpleNamespace

from bioseasy.app import setup_state

DONE = {"wifi_enabled_at": "2026-09-25T06:12:26Z", "encryption_enabled_at": "2026-09-25T06:14:33Z"}
FRESH = {"wifi_enabled_at": None, "encryption_enabled_at": None}
LIVE_BEING_REWRITTEN = SimpleNamespace(complete=False, encrypted=True)
LIVE_FINISHED = SimpleNamespace(complete=True, encrypted=True)


def test_a_mid_backup_live_folder_does_not_reopen_a_finished_setup():
    assert setup_state(DONE, LIVE_BEING_REWRITTEN, backed_up=True) == "done"


def test_the_first_backup_still_has_to_finish_once():
    assert setup_state(DONE, LIVE_BEING_REWRITTEN, backed_up=False) == "open"
    assert setup_state(DONE, None, backed_up=False) == "open"


def test_a_finished_live_backup_counts_without_a_run_row():
    assert setup_state(DONE, LIVE_FINISHED) == "done"


def test_wifi_and_encryption_are_still_required():
    assert setup_state(FRESH, LIVE_BEING_REWRITTEN, backed_up=True) == "open"
