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


async def test_full_flow_creates_entry(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CRITERION: CRITERION_TIME_ELAPSED}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == CRITERION_TIME_ELAPSED

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_NAME: "Oven filter", CONF_INTERVAL_DAYS: 30, CONF_WARN_THRESHOLD_PERCENT: 90},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Oven filter"
    assert result["data"] == {
        CONF_CRITERION: CRITERION_TIME_ELAPSED,
        CONF_NAME: "Oven filter",
        CONF_INTERVAL_DAYS: 30,
        CONF_WARN_THRESHOLD_PERCENT: 90,
    }


async def test_multiple_trackers_allowed(hass: HomeAssistant) -> None:
    """Each tracker is its own config entry; adding another must not abort."""
    for name in ("A", "B"):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_CRITERION: CRITERION_TIME_ELAPSED}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_NAME: name, CONF_INTERVAL_DAYS: 30, CONF_WARN_THRESHOLD_PERCENT: 90},
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
