"""Tests for the entity-on-duration criterion."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from freezegun import freeze_time

from custom_components.maintenance.const import (
    CONF_CRITERION,
    CONF_NAME,
    CONF_ON_STATE,
    CONF_TARGET_ENTITY,
    CONF_THRESHOLD,
    CONF_THRESHOLD_UNIT,
    CONF_WARN_THRESHOLD_PERCENT,
    CRITERION_ENTITY_ON_DURATION,
    STATE_OK,
    STATE_OVERDUE,
    UNIT_HOURS,
)

from .common import make_coordinator

TARGET = "input_boolean.oven"


def _config() -> dict:
    return {
        CONF_CRITERION: CRITERION_ENTITY_ON_DURATION,
        CONF_NAME: "Oven",
        CONF_TARGET_ENTITY: TARGET,
        CONF_ON_STATE: "on",
        CONF_THRESHOLD: 10,
        CONF_THRESHOLD_UNIT: UNIT_HOURS,
        CONF_WARN_THRESHOLD_PERCENT: 90,
    }


async def test_accumulates_on_time(hass):
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)

    with freeze_time(start) as frozen:
        hass.states.async_set(TARGET, "off")
        coord = await make_coordinator(hass, "t1", _config())
        await coord.async_mark_done()

        hass.states.async_set(TARGET, "on")
        await hass.async_block_till_done()

        frozen.move_to(start + timedelta(hours=2))
        hass.states.async_set(TARGET, "off")
        await hass.async_block_till_done()

    assert coord.data.counter == 2.0
    assert coord.data.state == STATE_OK


async def test_overdue_when_threshold_exceeded(hass):
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    with freeze_time(start) as frozen:
        hass.states.async_set(TARGET, "off")
        coord = await make_coordinator(hass, "t1", _config())
        await coord.async_mark_done()

        hass.states.async_set(TARGET, "on")
        await hass.async_block_till_done()

        frozen.move_to(start + timedelta(hours=11))
        hass.states.async_set(TARGET, "off")
        await hass.async_block_till_done()

    assert coord.data.state == STATE_OVERDUE
    assert coord.data.counter >= 11


async def test_counter_advances_while_entity_stays_on(hass):
    """Ticks between state changes must still advance the counter."""
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    with freeze_time(start) as frozen:
        hass.states.async_set(TARGET, "on")
        coord = await make_coordinator(hass, "t1", _config())
        await coord.async_mark_done()  # entity is on at mark_done
        assert coord.data.counter == 0.0

        # No state change — just time passing
        frozen.move_to(start + timedelta(hours=3))
        await coord.async_refresh()
        assert 2.9 < coord.data.counter < 3.1


async def test_mark_done_while_entity_on_reseeds(hass):
    """After mark_done with a currently-on entity, the counter must restart from 0
    and continue to accumulate."""
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    with freeze_time(start) as frozen:
        hass.states.async_set(TARGET, "on")
        coord = await make_coordinator(hass, "t1", _config())

        frozen.move_to(start + timedelta(hours=5))
        await coord.async_refresh()
        assert 4.9 < coord.data.counter < 5.1

        # mark done while entity is on
        await coord.async_mark_done()
        assert coord.data.counter == 0.0

        # 2 hours later, no state change — counter should show ~2h
        frozen.move_to(start + timedelta(hours=7))
        await coord.async_refresh()
        assert 1.9 < coord.data.counter < 2.1
