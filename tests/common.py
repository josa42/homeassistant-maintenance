"""Test helpers."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.maintenance.coordinator import (
    MaintenanceCoordinator,
    TrackerStore,
    build_coordinator,
)


async def make_coordinator(
    hass: HomeAssistant, tracker_id: str, config: dict[str, Any]
) -> MaintenanceCoordinator:
    """Create and start a coordinator with a fresh in-memory store."""
    store = TrackerStore(hass, f"entry_{tracker_id}")
    await store.async_load()
    coord = build_coordinator(hass, "entry", tracker_id, config, store)
    await coord.async_start()
    return coord
