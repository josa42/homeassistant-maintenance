"""Smoke test: full integration setup with a MockConfigEntry (one tracker)."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.maintenance.const import (
    CONF_CRITERION,
    CONF_INTERVAL,
    CONF_INTERVAL_UNIT,
    CONF_NAME,
    CRITERION_TIME_ELAPSED,
    DOMAIN,
    UNIT_DAYS,
)


async def test_setup_and_unload(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Oven",
        data={
            CONF_CRITERION: CRITERION_TIME_ELAPSED,
            CONF_NAME: "Oven",
            CONF_INTERVAL: 30,
            CONF_INTERVAL_UNIT: UNIT_DAYS,
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.runtime_data.coordinator is not None
    assert hass.states.get("sensor.oven").state == "ok"
    assert hass.states.get("button.oven_mark_done") is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
