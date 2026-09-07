"""The Maintenance integration — each config entry is one tracker."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import (
    CONF_INTERVAL,
    CONF_INTERVAL_UNIT,
    CONF_LAST_DONE,
    CONF_THRESHOLD,
    CONF_THRESHOLD_UNIT,
    UNIT_DAYS,
    UNIT_HOURS,
)
from .coordinator import MaintenanceCoordinator, TrackerStore, build_coordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

CARD_URL_PATH = "/maintenance-tracker/maintenance-card.js"
CARD_VERSION = "1.0.1"


@dataclass
class MaintenanceRuntimeData:
    store: TrackerStore
    coordinator: MaintenanceCoordinator


type MaintenanceConfigEntry = ConfigEntry[MaintenanceRuntimeData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the frontend card. Called once per HA session."""
    if hass.http is None:
        return True
    card_path = Path(__file__).parent / "www" / "maintenance-card.js"
    if not card_path.is_file():
        _LOGGER.warning("Maintenance card asset missing at %s", card_path)
        return True
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL_PATH, str(card_path), cache_headers=False)]
    )
    add_extra_js_url(hass, f"{CARD_URL_PATH}?v={CARD_VERSION}")
    _LOGGER.debug("Registered maintenance-card at %s", CARD_URL_PATH)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MaintenanceConfigEntry) -> bool:
    """Set up a maintenance tracker (one per config entry)."""
    store = TrackerStore(hass, entry.entry_id)
    await store.async_load()

    # last_done in entry.data is a one-shot seed: apply it to the persisted
    # tracker state, then strip it from the entry so it doesn't clobber
    # future updates from mark_done on the next reload.
    raw_last_done = entry.data.get(CONF_LAST_DONE)
    if raw_last_done:
        parsed = dt_util.parse_datetime(str(raw_last_done))
        if parsed is not None:
            store.get(entry.entry_id).last_done_date = dt_util.as_utc(parsed)
            await store.async_save_now()
        new_data = {k: v for k, v in entry.data.items() if k != CONF_LAST_DONE}
        hass.config_entries.async_update_entry(entry, data=new_data)

    coordinator = build_coordinator(
        hass, entry.entry_id, entry.entry_id, dict(entry.data), store
    )
    await coordinator.async_start()
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = MaintenanceRuntimeData(store=store, coordinator=coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MaintenanceConfigEntry) -> bool:
    """Tear down the tracker."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unloaded:
        return False
    entry.runtime_data.coordinator.async_stop()
    await entry.runtime_data.store.async_save_now()
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: MaintenanceConfigEntry) -> None:
    """Reload when reconfigured."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entries: interval_days → interval+interval_unit=days, likewise threshold_hours."""
    data = dict(entry.data)
    changed = False
    if "interval_days" in data:
        data[CONF_INTERVAL] = data.pop("interval_days")
        data.setdefault(CONF_INTERVAL_UNIT, UNIT_DAYS)
        changed = True
    if "threshold_hours" in data:
        data[CONF_THRESHOLD] = data.pop("threshold_hours")
        data.setdefault(CONF_THRESHOLD_UNIT, UNIT_HOURS)
        changed = True
    if changed:
        hass.config_entries.async_update_entry(entry, data=data, version=2)
    else:
        hass.config_entries.async_update_entry(entry, version=2)
    return True
