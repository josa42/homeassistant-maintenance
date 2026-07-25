"""Tests for the template_boolean criterion."""

from __future__ import annotations

from custom_components.maintenance.const import (
    CONF_CRITERION,
    CONF_NAME,
    CONF_TEMPLATE,
    CONF_WARN_THRESHOLD_PERCENT,
    CRITERION_TEMPLATE_BOOLEAN,
    STATE_OK,
    STATE_OVERDUE,
)

from .common import make_coordinator


def _config(template: str) -> dict:
    return {
        CONF_CRITERION: CRITERION_TEMPLATE_BOOLEAN,
        CONF_NAME: "Tpl",
        CONF_TEMPLATE: template,
        CONF_WARN_THRESHOLD_PERCENT: 90,
    }


async def test_true_template_is_overdue(hass):
    coord = await make_coordinator(hass, "t1", _config("{{ true }}"))
    await coord.async_refresh()
    assert coord.data.state == STATE_OVERDUE


async def test_false_template_is_ok(hass):
    coord = await make_coordinator(hass, "t2", _config("{{ false }}"))
    await coord.async_refresh()
    assert coord.data.state == STATE_OK


async def test_state_follows_entity(hass):
    hass.states.async_set("input_boolean.foo", "off")
    coord = await make_coordinator(
        hass, "t3", _config("{{ is_state('input_boolean.foo', 'on') }}")
    )
    await coord.async_refresh()
    assert coord.data.state == STATE_OK

    hass.states.async_set("input_boolean.foo", "on")
    await hass.async_block_till_done()
    await coord.async_refresh()
    assert coord.data.state == STATE_OVERDUE
