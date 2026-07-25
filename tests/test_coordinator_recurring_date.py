"""Tests for the recurring_date criterion."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from freezegun import freeze_time

from custom_components.maintenance.const import (
    CONF_CRITERION,
    CONF_DAY_OF_MONTH,
    CONF_MONTH_OF_YEAR,
    CONF_NAME,
    CONF_WARN_DAYS_BEFORE,
    CRITERION_RECURRING_DATE,
    MONTH_ANY,
    STATE_DUE_SOON,
    STATE_OK,
    STATE_OVERDUE,
)

from .common import make_coordinator


def _monthly(day: int = 5, warn_days: int = 3) -> dict:
    return {
        CONF_CRITERION: CRITERION_RECURRING_DATE,
        CONF_NAME: "Monthly",
        CONF_DAY_OF_MONTH: day,
        CONF_MONTH_OF_YEAR: MONTH_ANY,
        CONF_WARN_DAYS_BEFORE: warn_days,
    }


def _yearly(day: int, month: int, warn_days: int = 3) -> dict:
    return {
        CONF_CRITERION: CRITERION_RECURRING_DATE,
        CONF_NAME: "Yearly",
        CONF_DAY_OF_MONTH: day,
        CONF_MONTH_OF_YEAR: str(month),
        CONF_WARN_DAYS_BEFORE: warn_days,
    }


async def test_monthly_due_is_next_5th(hass):
    with freeze_time(datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc)):
        coord = await make_coordinator(hass, "t1", _monthly(5, warn_days=3))
        await coord.async_mark_done()
    assert coord.data.estimated_due_date.date() == datetime(2026, 9, 5).date()
    assert coord.data.state == STATE_OK

    # 4 days before next → still OK (warn = 3 days).
    with freeze_time(datetime(2026, 9, 1, tzinfo=timezone.utc)):
        await coord.async_refresh()
        assert coord.data.state == STATE_OK

    # 2 days before next → DUE_SOON.
    with freeze_time(datetime(2026, 9, 3, tzinfo=timezone.utc)):
        await coord.async_refresh()
        assert coord.data.state == STATE_DUE_SOON

    # After the next date without marking → OVERDUE.
    with freeze_time(datetime(2026, 9, 6, tzinfo=timezone.utc)):
        await coord.async_refresh()
        assert coord.data.state == STATE_OVERDUE


async def test_yearly_due_next_year_after_pass(hass):
    with freeze_time(datetime(2026, 10, 1, tzinfo=timezone.utc)):
        coord = await make_coordinator(hass, "t2", _yearly(1, 10))
        await coord.async_mark_done()
    assert coord.data.estimated_due_date.date() == datetime(2027, 10, 1).date()

    with freeze_time(datetime(2027, 10, 2, tzinfo=timezone.utc)):
        await coord.async_refresh()
        assert coord.data.state == STATE_OVERDUE


async def test_day_31_clamped_in_february(hass):
    with freeze_time(datetime(2026, 1, 31, tzinfo=timezone.utc)):
        coord = await make_coordinator(hass, "t3", _monthly(31))
        await coord.async_mark_done()
    # Next occurrence should be clamped to Feb 28 (2026 is not a leap year).
    assert coord.data.estimated_due_date.date() == datetime(2026, 2, 28).date()


async def test_progress_anchored_to_calendar_regardless_of_mark_done(hass):
    """Progress must always reflect elapsed time between the previous and next
    scheduled dates, not between last_done and next scheduled date."""
    # Mark done LATE (Aug 10) — after the Aug 5 scheduled date.
    with freeze_time(datetime(2026, 8, 10, tzinfo=timezone.utc)):
        coord = await make_coordinator(hass, "t4", _monthly(5))
        await coord.async_mark_done()

    # On Aug 20: prev=Aug 5, next=Sep 5, elapsed=15d, interval=31d → ~48%.
    with freeze_time(datetime(2026, 8, 20, tzinfo=timezone.utc)):
        await coord.async_refresh()
        assert 47 < coord.data.progress < 50, coord.data.progress
        # Not overdue: last_done (Aug 10) >= prev_due (Aug 5)
        assert coord.data.state == STATE_OK
