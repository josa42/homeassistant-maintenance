"""Maintenance tracker sensor — one per config entry."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SERVICE_MARK_DONE,
    SERVICE_RESET,
    STATE_DUE_SOON,
    STATE_OK,
    STATE_OVERDUE,
)
from .coordinator import MaintenanceCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create the tracker sensor for this config entry."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities([MaintenanceSensor(coordinator, entry.title)])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_MARK_DONE,
        {vol.Optional("date"): cv.datetime},
        _async_service_mark_done,
    )
    platform.async_register_entity_service(
        SERVICE_RESET,
        {},
        _async_service_reset,
    )


async def _async_service_mark_done(entity: "MaintenanceSensor", call: ServiceCall) -> None:
    await entity.coordinator.async_mark_done(call.data.get("date"))


async def _async_service_reset(entity: "MaintenanceSensor", call: ServiceCall) -> None:
    await entity.coordinator.async_reset_counter()


class MaintenanceSensor(CoordinatorEntity[MaintenanceCoordinator], SensorEntity):
    """Sensor representing one maintenance tracker."""

    _attr_has_entity_name = True
    _attr_translation_key = "tracker"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [STATE_OK, STATE_DUE_SOON, STATE_OVERDUE]

    def __init__(self, coordinator: MaintenanceCoordinator, title: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.tracker_id
        self._attr_name = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.tracker_id)},
            name=title,
            manufacturer="Maintenance Tracker",
            model="Tracker",
        )

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.state

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.as_attributes()
