"""The Maintenance integration — each config entry is one tracker."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import MaintenanceCoordinator, TrackerStore, build_coordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]


@dataclass
class MaintenanceRuntimeData:
    store: TrackerStore
    coordinator: MaintenanceCoordinator


type MaintenanceConfigEntry = ConfigEntry[MaintenanceRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: MaintenanceConfigEntry) -> bool:
    """Set up a maintenance tracker (one per config entry)."""
    store = TrackerStore(hass, entry.entry_id)
    await store.async_load()

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
