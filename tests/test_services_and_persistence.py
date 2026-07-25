"""Tests for mark_done event firing and persistence via Store."""

from __future__ import annotations

from datetime import datetime, timezone

from freezegun import freeze_time

from custom_components.maintenance.const import (
    CONF_CRITERION,
    CONF_INTERVAL,
    CONF_INTERVAL_UNIT,
    CONF_NAME,
    CRITERION_TIME_ELAPSED,
    EVENT_MAINTENANCE_COMPLETED,
    STATE_OK,
    UNIT_DAYS,
)
from custom_components.maintenance.coordinator import TrackerStore, build_coordinator

from .common import make_coordinator


def _config() -> dict:
    return {
        CONF_CRITERION: CRITERION_TIME_ELAPSED,
        CONF_NAME: "Filter",
        CONF_INTERVAL: 30,
        CONF_INTERVAL_UNIT: UNIT_DAYS,
    }


async def test_mark_done_fires_event(hass):
    events = []
    hass.bus.async_listen(EVENT_MAINTENANCE_COMPLETED, lambda e: events.append(e))

    coord = await make_coordinator(hass, "t1", _config())
    await coord.async_mark_done()
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data["tracker_id"] == "t1"


async def test_persistence_survives_restart(hass, tmp_path):
    """Data written to Store must be readable by a fresh coordinator/store."""
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    with freeze_time(start):
        coord = await make_coordinator(hass, "t1", _config())
        await coord.async_mark_done()
        await coord.store.async_save_now()
        await hass.async_block_till_done()

    # Fresh store loading from the same key should see the persisted last_done
    with freeze_time(start):
        fresh_store = TrackerStore(hass, "entry_t1")
        await fresh_store.async_load()
        assert fresh_store.get("t1").last_done_date == start

        fresh_coord = build_coordinator(hass, "entry", "t1", _config(), fresh_store)
        await fresh_coord.async_refresh()
    assert fresh_coord.data.state == STATE_OK
    assert fresh_coord.data.last_done_date == start
