"""Verify that CONF_LAST_DONE in entry.data seeds the persisted last-done date."""

from __future__ import annotations

from datetime import datetime, timezone

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.maintenance.const import (
    CONF_CRITERION,
    CONF_INTERVAL,
    CONF_INTERVAL_UNIT,
    CONF_LAST_DONE,
    CONF_NAME,
    CRITERION_TIME_ELAPSED,
    DOMAIN,
    UNIT_DAYS,
)


async def test_last_done_is_applied_and_stripped(hass):
    seeded = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Oven",
        data={
            CONF_CRITERION: CRITERION_TIME_ELAPSED,
            CONF_NAME: "Oven",
            CONF_INTERVAL: 30,
            CONF_INTERVAL_UNIT: UNIT_DAYS,
            CONF_LAST_DONE: seeded.isoformat(),
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Persisted state should reflect the seed.
    assert entry.runtime_data.store.get(entry.entry_id).last_done_date == seeded
    # Entry data should no longer contain the seed (one-shot).
    assert CONF_LAST_DONE not in entry.data
