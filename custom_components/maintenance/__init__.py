"""The Maintenance integration."""

from __future__ import annotations

from dataclasses import dataclass, field

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, SUBENTRY_TYPE_TRACKER
from .coordinator import MaintenanceCoordinator, TrackerStore, build_coordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]


@dataclass
class MaintenanceRuntimeData:
    store: TrackerStore
    coordinators: dict[str, MaintenanceCoordinator] = field(default_factory=dict)


type MaintenanceConfigEntry = ConfigEntry[MaintenanceRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: MaintenanceConfigEntry) -> bool:
    """Set up the Maintenance integration: build one coordinator per tracker subentry."""
    store = TrackerStore(hass, entry.entry_id)
    await store.async_load()

    runtime = MaintenanceRuntimeData(store=store)
    entry.runtime_data = runtime

    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != SUBENTRY_TYPE_TRACKER:
            continue
        coordinator = build_coordinator(
            hass, entry.entry_id, subentry_id, dict(subentry.data), store
        )
        runtime.coordinators[subentry_id] = coordinator
        await coordinator.async_start()
        await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MaintenanceConfigEntry) -> bool:
    """Tear down the integration."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unloaded:
        return False
    for coordinator in entry.runtime_data.coordinators.values():
        coordinator.async_stop()
    await entry.runtime_data.store.async_save_now()
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: MaintenanceConfigEntry) -> None:
    """Reload when a subentry is added, removed, or reconfigured."""
    await hass.config_entries.async_reload(entry.entry_id)
