"""Tests for the entity-on-duration criterion."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from freezegun import freeze_time

from custom_components.maintenance.const import (
    CONF_CRITERION,
    CONF_NAME,
    CONF_ON_STATE,
    CONF_TARGET_ENTITY,
    CONF_THRESHOLD_HOURS,
    CONF_WARN_THRESHOLD_PERCENT,
    CRITERION_ENTITY_ON_DURATION,
    STATE_OK,
    STATE_OVERDUE,
)

from .common import make_coordinator

TARGET = "input_boolean.oven"


def _config() -> dict:
    return {
        CONF_CRITERION: CRITERION_ENTITY_ON_DURATION,
        CONF_NAME: "Oven",
        CONF_TARGET_ENTITY: TARGET,
        CONF_ON_STATE: "on",
        CONF_THRESHOLD_HOURS: 10,
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
