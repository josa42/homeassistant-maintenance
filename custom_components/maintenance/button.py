"""Mark-done button — one per tracker subentry."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, SUBENTRY_TYPE_TRACKER
from .coordinator import MaintenanceCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create one mark-done button per tracker subentry."""
    runtime = entry.runtime_data
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != SUBENTRY_TYPE_TRACKER:
            continue
        coordinator = runtime.coordinators[subentry_id]
        async_add_entities(
            [MarkDoneButton(coordinator, subentry.title)],
            config_subentry_id=subentry_id,
        )


class MarkDoneButton(ButtonEntity):
    """Button that marks the maintenance as done."""

    _attr_has_entity_name = True
    _attr_translation_key = "mark_done"

    def __init__(self, coordinator: MaintenanceCoordinator, title: str) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.tracker_id}_mark_done"
        self._attr_name = "Mark done"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.tracker_id)},
            name=title,
            manufacturer="Maintenance Tracker",
            model="Tracker",
        )

    async def async_press(self) -> None:
        await self.coordinator.async_mark_done()
