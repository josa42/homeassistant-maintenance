"""Tests for the entity-usage-count criterion."""

from __future__ import annotations

from datetime import datetime, timezone

from freezegun import freeze_time

from custom_components.maintenance.const import (
    CONF_CRITERION,
    CONF_FROM_STATE,
    CONF_NAME,
    CONF_TARGET_ENTITY,
    CONF_THRESHOLD_COUNT,
    CONF_TO_STATE,
    CONF_WARN_THRESHOLD_PERCENT,
    CRITERION_ENTITY_USAGE_COUNT,
    STATE_OK,
    STATE_OVERDUE,
)

from .common import make_coordinator

TARGET = "input_boolean.washer"


def _config() -> dict:
    return {
        CONF_CRITERION: CRITERION_ENTITY_USAGE_COUNT,
        CONF_NAME: "Washer",
        CONF_TARGET_ENTITY: TARGET,
        CONF_FROM_STATE: "off",
        CONF_TO_STATE: "on",
        CONF_THRESHOLD_COUNT: 3,
        CONF_WARN_THRESHOLD_PERCENT: 90,
    }


async def _toggle(hass, from_state: str, to_state: str) -> None:
    hass.states.async_set(TARGET, from_state)
    await hass.async_block_till_done()
    hass.states.async_set(TARGET, to_state)
    await hass.async_block_till_done()


async def test_counts_matching_transitions(hass):
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    with freeze_time(start):
        hass.states.async_set(TARGET, "off")
        coord = await make_coordinator(hass, "t1", _config())
        await coord.async_mark_done()

        await _toggle(hass, "off", "on")
        await _toggle(hass, "on", "off")
        await _toggle(hass, "off", "on")

    assert coord.data.counter == 2
    assert coord.data.state == STATE_OK


async def test_overdue_when_count_exceeded(hass):
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    with freeze_time(start):
        hass.states.async_set(TARGET, "off")
        coord = await make_coordinator(hass, "t1", _config())
        await coord.async_mark_done()

        for _ in range(4):
            await _toggle(hass, "off", "on")
            await _toggle(hass, "on", "off")

    assert coord.data.counter == 4
    assert coord.data.state == STATE_OVERDUE
