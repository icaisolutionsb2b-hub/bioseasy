# SPDX-License-Identifier: GPL-3.0-or-later
"""Notification text: one sober title and body per event. Delivery is ntfy.py's job."""

from __future__ import annotations


def _kind(product_type: str | None) -> str:
    """ "iPhone" or "iPad" - the same distinction app.py's device_kind() draws for the setup
    wizard and device page, duplicated here as one line rather than importing app.py (which
    imports this module, so that would be a cycle)."""
    return "iPad" if product_type and product_type.startswith("iPad") else "iPhone"


def message_for(event: str, device_name: str, detail: str = "", product_type: str | None = None) -> tuple[str, str]:
    """Sober, short title and body for one notification event.

    `product_type` is only used by the "upcoming" event, to pick "iPhone" or "iPad" wording;
    every other event ignores it.
    """
    name = device_name or "the device"
    if event == "upcoming":
        kind = _kind(product_type)
        minutes = detail or "a few"
        return (
            f"Backup of {name} starts soon",
            f"Backup of {name} starts in {minutes} minutes: put the {kind} on the charger, "
            "unlock it and wait for the passcode prompt.",
        )
    if event == "waiting_for_passcode":
        return f"Confirm the backup on {name}", "Unlock the device and enter its passcode to start the backup."
    if event == "due":
        return (
            f"Backup of {name} is due",
            detail or "Open bioseasy on the device and tap Back up now, then enter the passcode.",
        )
    if event == "succeeded":
        return f"Backup of {name} succeeded", "The backup finished and reads as complete on disk."
    if event == "failed":
        return f"Backup of {name} failed", detail or "The backup did not finish. See the device page for details."
    if event == "not_confirmed":
        return (
            f"Backup of {name} not confirmed",
            "Nobody entered the passcode in time, so the backup did not run.",
        )
    if event == "overdue":
        return (
            f"{name} is overdue for a backup",
            detail or "No complete backup has finished within the configured period.",
        )
    if event == "storage_failed":
        return "Backup storage problem", detail or "The backup storage is not ready. See the storage page."
    raise ValueError(f"Unknown notification event: {event!r}")
