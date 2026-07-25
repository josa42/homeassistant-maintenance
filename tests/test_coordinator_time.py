"""Tests for the time-elapsed criterion."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from freezegun import freeze_time

from custom_components.maintenance.const import (
    CONF_CRITERION,
    CONF_INTERVAL,
    CONF_INTERVAL_UNIT,
    CONF_NAME,
    CONF_WARN_THRESHOLD_PERCENT,
    CRITERION_TIME_ELAPSED,
    STATE_DUE_SOON,
    STATE_OK,
    STATE_OVERDUE,
    UNIT_DAYS,
    UNIT_MONTHS,
)

from .common import make_coordinator


def _config(interval: float = 10, unit: str = UNIT_DAYS) -> dict:
    return {
        CONF_CRITERION: CRITERION_TIME_ELAPSED,
        CONF_NAME: "Oven cleaning",
        CONF_INTERVAL: interval,
        CONF_INTERVAL_UNIT: unit,
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


async def test_months_unit(hass):
    """A 3-month interval reports counter in months and computes progress in seconds."""
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    with freeze_time(start):
        coord = await make_coordinator(hass, "t1", _config(interval=3, unit=UNIT_MONTHS))
        await coord.async_mark_done()
        assert coord.data.counter_unit == UNIT_MONTHS
        assert coord.data.threshold == 3
        assert coord.data.progress == 0.0

    # 1.5 months ~= 45.66 days
    with freeze_time(start + timedelta(days=46)):
        await coord.async_refresh()
        assert 49 < coord.data.progress < 52
        assert 1.4 < coord.data.counter < 1.6
