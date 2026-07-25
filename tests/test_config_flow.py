"""Tests for the config flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.maintenance.const import (
    CONF_CRITERION,
    CONF_INTERVAL_DAYS,
    CONF_NAME,
    CONF_WARN_THRESHOLD_PERCENT,
    CRITERION_TIME_ELAPSED,
    DOMAIN,
)


async def test_single_instance(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Maintenance"

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] in ("single_instance_allowed", "already_configured")


async def test_time_elapsed_subentry_smoke(hass: HomeAssistant) -> None:
    """Smoke test that the criterion picker returns the time_elapsed form."""
    from custom_components.maintenance.config_flow import TrackerSubentryFlowHandler

    handler = TrackerSubentryFlowHandler()
    # Show the first step
    result = await handler.async_step_user(None)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # Choose time_elapsed → get details form
    result = await handler.async_step_user({CONF_CRITERION: CRITERION_TIME_ELAPSED})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == CRITERION_TIME_ELAPSED
