"""Tests for the template_numeric criterion."""

from __future__ import annotations

from custom_components.maintenance.const import (
    CONF_CRITERION,
    CONF_NAME,
    CONF_TEMPLATE,
    CONF_THRESHOLD,
    CONF_WARN_THRESHOLD_PERCENT,
    CRITERION_TEMPLATE_NUMERIC,
    STATE_DUE_SOON,
    STATE_OK,
    STATE_OVERDUE,
)

from .common import make_coordinator


def _config(template: str, threshold: float = 10, warn: int = 90) -> dict:
    return {
        CONF_CRITERION: CRITERION_TEMPLATE_NUMERIC,
        CONF_NAME: "Tpl",
        CONF_TEMPLATE: template,
        CONF_THRESHOLD: threshold,
        CONF_WARN_THRESHOLD_PERCENT: warn,
    }


async def test_low_value_is_ok(hass):
    coord = await make_coordinator(hass, "t1", _config("{{ 5 }}", threshold=10))
    await coord.async_refresh()
    assert coord.data.state == STATE_OK
    assert coord.data.counter == 5
    assert coord.data.progress == 50


async def test_high_value_is_due_soon(hass):
    coord = await make_coordinator(hass, "t2", _config("{{ 9 }}", threshold=10, warn=90))
    await coord.async_refresh()
    assert coord.data.state == STATE_DUE_SOON


async def test_over_threshold_is_overdue(hass):
    coord = await make_coordinator(hass, "t3", _config("{{ 12 }}", threshold=10))
    await coord.async_refresh()
    assert coord.data.state == STATE_OVERDUE
    assert coord.data.progress == 120


async def test_reacts_to_entity_state(hass):
    hass.states.async_set("sensor.hours", "1")
    coord = await make_coordinator(
        hass,
        "t4",
        _config("{{ states('sensor.hours') | float(0) }}", threshold=10, warn=90),
    )
    await coord.async_refresh()
    assert coord.data.state == STATE_OK

    hass.states.async_set("sensor.hours", "11")
    await hass.async_block_till_done()
    await coord.async_refresh()
    assert coord.data.state == STATE_OVERDUE
