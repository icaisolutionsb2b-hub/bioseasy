# SPDX-License-Identifier: GPL-3.0-or-later
import pytest

from bioseasy import notify


@pytest.mark.parametrize(
    "event",
    ["waiting_for_passcode", "succeeded", "failed", "not_confirmed", "overdue", "storage_failed", "upcoming"],
)
def test_message_for_covers_every_event(event):
    title, body = notify.message_for(event, "Anna's iPhone", "some detail")
    assert title and body
    assert "\n" not in title


def test_message_for_unknown_event_raises():
    with pytest.raises(ValueError):
        notify.message_for("no-such-event", "device")


def test_message_for_upcoming_names_minutes_and_iphone_or_ipad():
    _, body_phone = notify.message_for("upcoming", "Anna's iPhone", "5", "iPhone14,5")
    assert "starts in 5 minutes" in body_phone
    assert "iPhone" in body_phone
    assert "charger" in body_phone
    assert "passcode prompt" in body_phone

    _, body_pad = notify.message_for("upcoming", "Anna's iPad", "5", "iPad13,1")
    assert "iPad" in body_pad
