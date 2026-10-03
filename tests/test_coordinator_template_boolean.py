"""Tests for the template_boolean criterion."""

from __future__ import annotations

from datetime import datetime, timezone

from freezegun import freeze_time

from custom_components.maintenance.const import (
    CONF_COOLDOWN,
    CONF_COOLDOWN_UNIT,
    CONF_CRITERION,
    CONF_NAME,
    CONF_TEMPLATE,
    CONF_WARN_THRESHOLD_PERCENT,
    CRITERION_TEMPLATE_BOOLEAN,
    STATE_OK,
    STATE_OVERDUE,
    UNIT_DAYS,
)
from custom_components.maintenance.coordinator import TrackerStore, build_coordinator

from .common import make_coordinator

_FLAG = "{{ is_state('input_boolean.frost', 'on') }}"


def _config(template: str, cooldown_days: int | None = None) -> dict:
    config = {
        CONF_CRITERION: CRITERION_TEMPLATE_BOOLEAN,
        CONF_NAME: "Tpl",
        CONF_TEMPLATE: template,
        CONF_WARN_THRESHOLD_PERCENT: 90,
    }
    if cooldown_days is not None:
        config[CONF_COOLDOWN] = cooldown_days
        config[CONF_COOLDOWN_UNIT] = UNIT_DAYS
    return config


async def _set(hass, coord, state: str) -> None:
    hass.states.async_set("input_boolean.frost", state)
    await hass.async_block_till_done()
    await coord.async_refresh()


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


async def test_mark_done_silences_until_condition_clears(hass):
    hass.states.async_set("input_boolean.frost", "on")
    coord = await make_coordinator(hass, "t4", _config(_FLAG))
    await coord.async_refresh()
    assert coord.data.state == STATE_OVERDUE

    await coord.async_mark_done()
    assert coord.data.state == STATE_OK
    assert coord.data.silenced is True

    await _set(hass, coord, "off")
    assert coord.data.state == STATE_OK
    assert coord.data.silenced is False

    await _set(hass, coord, "on")
    assert coord.data.state == STATE_OVERDUE


async def test_mark_done_while_inactive_does_not_silence(hass):
    hass.states.async_set("input_boolean.frost", "off")
    coord = await make_coordinator(hass, "t5", _config(_FLAG))
    await coord.async_mark_done()
    assert coord.data.silenced is False

    await _set(hass, coord, "on")
    assert coord.data.state == STATE_OVERDUE


async def test_cooldown_keeps_silenced_after_condition_clears(hass):
    done = datetime(2026, 10, 1, tzinfo=timezone.utc)
    hass.states.async_set("input_boolean.frost", "on")
    coord = await make_coordinator(hass, "t6", _config(_FLAG, cooldown_days=150))

    with freeze_time(done):
        await coord.async_mark_done()
        assert coord.data.state == STATE_OK

    with freeze_time(datetime(2027, 1, 10, tzinfo=timezone.utc)):
        await _set(hass, coord, "off")
        await _set(hass, coord, "on")
        assert coord.data.state == STATE_OK
        assert coord.data.silenced is True

    with freeze_time(datetime(2027, 3, 1, tzinfo=timezone.utc)):
        await coord.async_refresh()
        assert coord.data.state == STATE_OVERDUE
        assert coord.data.silenced is False


async def test_cooldown_requires_condition_to_clear(hass):
    hass.states.async_set("input_boolean.frost", "on")
    coord = await make_coordinator(hass, "t7", _config(_FLAG, cooldown_days=1))

    with freeze_time(datetime(2026, 10, 1, tzinfo=timezone.utc)):
        await coord.async_mark_done()

    with freeze_time(datetime(2026, 10, 5, tzinfo=timezone.utc)):
        await coord.async_refresh()
        assert coord.data.state == STATE_OK

        await _set(hass, coord, "off")
        await _set(hass, coord, "on")
        assert coord.data.state == STATE_OVERDUE


async def test_silenced_survives_restart(hass):
    hass.states.async_set("input_boolean.frost", "on")
    coord = await make_coordinator(hass, "t8", _config(_FLAG))
    await coord.async_mark_done()
    await coord.store.async_save_now()
    coord.async_stop()

    fresh_store = TrackerStore(hass, "entry_t8")
    await fresh_store.async_load()
    fresh = build_coordinator(hass, "entry", "t8", _config(_FLAG), fresh_store)
    await fresh.async_start()
    await fresh.async_refresh()
    assert fresh.data.state == STATE_OK
    assert fresh.data.silenced is True
