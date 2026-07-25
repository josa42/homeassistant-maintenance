"""Tests for the time-elapsed criterion."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from freezegun import freeze_time

from custom_components.maintenance.const import (
    CONF_CRITERION,
    CONF_INTERVAL_DAYS,
    CONF_NAME,
    CONF_WARN_THRESHOLD_PERCENT,
    CRITERION_TIME_ELAPSED,
    STATE_DUE_SOON,
    STATE_OK,
    STATE_OVERDUE,
)

from .common import make_coordinator


def _config() -> dict:
    return {
        CONF_CRITERION: CRITERION_TIME_ELAPSED,
        CONF_NAME: "Oven cleaning",
        CONF_INTERVAL_DAYS: 10,
        CONF_WARN_THRESHOLD_PERCENT: 90,
    }


async def test_starts_ok_after_mark_done(hass):
    start = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    with freeze_time(start):
        coord = await make_coordinator(hass, "t1", _config())
        await coord.async_mark_done()
    assert coord.data.state == STATE_OK
    assert coord.data.progress == 0.0
    assert coord.data.last_done_date == start
    assert coord.data.estimated_due_date == start + timedelta(days=10)


async def test_transitions_ok_due_soon_overdue(hass):
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    with freeze_time(start):
        coord = await make_coordinator(hass, "t1", _config())
        await coord.async_mark_done()

    with freeze_time(start + timedelta(days=5)):
        await coord.async_refresh()
        assert coord.data.state == STATE_OK
        assert 49 < coord.data.progress < 51

    with freeze_time(start + timedelta(days=9, hours=1)):
        await coord.async_refresh()
        assert coord.data.state == STATE_DUE_SOON

    with freeze_time(start + timedelta(days=11)):
        await coord.async_refresh()
        assert coord.data.state == STATE_OVERDUE
        assert coord.data.progress > 100
