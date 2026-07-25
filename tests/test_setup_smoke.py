"""Smoke test: full integration setup with a MockConfigEntry."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.maintenance.const import (
    CONF_CRITERION,
    CONF_INTERVAL_DAYS,
    CONF_NAME,
    CRITERION_TIME_ELAPSED,
    DOMAIN,
    SUBENTRY_TYPE_TRACKER,
)


async def test_setup_and_unload(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Maintenance",
        data={},
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.runtime_data is not None
    assert entry.runtime_data.coordinators == {}

    assert await hass.config_entries.async_unload(entry.entry_id)
