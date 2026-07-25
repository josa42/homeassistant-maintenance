"""Version-1 → version-2 migration test."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.maintenance.const import (
    CONF_CRITERION,
    CONF_INTERVAL,
    CONF_INTERVAL_UNIT,
    CONF_NAME,
    CONF_THRESHOLD,
    CONF_THRESHOLD_UNIT,
    CRITERION_ENTITY_ON_DURATION,
    CRITERION_TIME_ELAPSED,
    DOMAIN,
    UNIT_DAYS,
    UNIT_HOURS,
)


async def test_time_elapsed_migrates_from_v1(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Old filter",
        data={
            CONF_CRITERION: CRITERION_TIME_ELAPSED,
            CONF_NAME: "Old filter",
            "interval_days": 30,
        },
        version=1,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 2
    assert entry.data[CONF_INTERVAL] == 30
    assert entry.data[CONF_INTERVAL_UNIT] == UNIT_DAYS
    assert "interval_days" not in entry.data


async def test_entity_on_duration_migrates_from_v1(hass):
    hass.states.async_set("input_boolean.oven", "off")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Old oven",
        data={
            CONF_CRITERION: CRITERION_ENTITY_ON_DURATION,
            CONF_NAME: "Old oven",
            "target_entity_id": "input_boolean.oven",
            "on_state": "on",
            "threshold_hours": 100,
        },
        version=1,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 2
    assert entry.data[CONF_THRESHOLD] == 100
    assert entry.data[CONF_THRESHOLD_UNIT] == UNIT_HOURS
    assert "threshold_hours" not in entry.data
