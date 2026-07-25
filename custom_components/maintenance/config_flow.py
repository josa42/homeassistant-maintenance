"""Config flow for the Maintenance integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CRITERION,
    CONF_FROM_STATE,
    CONF_INTERVAL_DAYS,
    CONF_NAME,
    CONF_ON_STATE,
    CONF_TARGET_ENTITY,
    CONF_THRESHOLD_COUNT,
    CONF_THRESHOLD_HOURS,
    CONF_TO_STATE,
    CONF_WARN_THRESHOLD_PERCENT,
    CRITERION_ENTITY_ON_DURATION,
    CRITERION_ENTITY_USAGE_COUNT,
    CRITERION_MANUAL,
    CRITERION_TIME_ELAPSED,
    DEFAULT_FROM_STATE,
    DEFAULT_ON_STATE,
    DEFAULT_TO_STATE,
    DEFAULT_WARN_THRESHOLD_PERCENT,
    DOMAIN,
    SUBENTRY_TYPE_TRACKER,
)

_WARN_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(min=1, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
)
_NAME_SELECTOR = selector.TextSelector()
_ENTITY_SELECTOR = selector.EntitySelector()
_TEXT_SELECTOR = selector.TextSelector()

_CRITERION_SCHEMAS: dict[str, vol.Schema] = {
    CRITERION_TIME_ELAPSED: vol.Schema(
        {
            vol.Required(CONF_NAME): _NAME_SELECTOR,
            vol.Required(CONF_INTERVAL_DAYS): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(CONF_WARN_THRESHOLD_PERCENT, default=DEFAULT_WARN_THRESHOLD_PERCENT): _WARN_SELECTOR,
        }
    ),
    CRITERION_ENTITY_ON_DURATION: vol.Schema(
        {
            vol.Required(CONF_NAME): _NAME_SELECTOR,
            vol.Required(CONF_TARGET_ENTITY): _ENTITY_SELECTOR,
            vol.Required(CONF_ON_STATE, default=DEFAULT_ON_STATE): _TEXT_SELECTOR,
            vol.Required(CONF_THRESHOLD_HOURS): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0.5, step=0.5, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(CONF_WARN_THRESHOLD_PERCENT, default=DEFAULT_WARN_THRESHOLD_PERCENT): _WARN_SELECTOR,
        }
    ),
    CRITERION_ENTITY_USAGE_COUNT: vol.Schema(
        {
            vol.Required(CONF_NAME): _NAME_SELECTOR,
            vol.Required(CONF_TARGET_ENTITY): _ENTITY_SELECTOR,
            vol.Required(CONF_FROM_STATE, default=DEFAULT_FROM_STATE): _TEXT_SELECTOR,
            vol.Required(CONF_TO_STATE, default=DEFAULT_TO_STATE): _TEXT_SELECTOR,
            vol.Required(CONF_THRESHOLD_COUNT): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(CONF_WARN_THRESHOLD_PERCENT, default=DEFAULT_WARN_THRESHOLD_PERCENT): _WARN_SELECTOR,
        }
    ),
    CRITERION_MANUAL: vol.Schema(
        {
            vol.Required(CONF_NAME): _NAME_SELECTOR,
            vol.Required(CONF_WARN_THRESHOLD_PERCENT, default=DEFAULT_WARN_THRESHOLD_PERCENT): _WARN_SELECTOR,
        }
    ),
}


class MaintenanceConfigFlow(ConfigFlow, domain=DOMAIN):
    """Parent config flow — single integration entry that owns tracker subentries."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Maintenance", data={})

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_TYPE_TRACKER: TrackerSubentryFlowHandler}


class TrackerSubentryFlowHandler(ConfigSubentryFlow):
    """Add or reconfigure a single maintenance tracker."""

    def __init__(self) -> None:
        self._criterion: str | None = None
        self._existing_data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if user_input is not None:
            self._criterion = user_input[CONF_CRITERION]
            return await self._async_show_details_step()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CRITERION, default=CRITERION_TIME_ELAPSED): vol.In(
                        [
                            CRITERION_TIME_ELAPSED,
                            CRITERION_ENTITY_ON_DURATION,
                            CRITERION_ENTITY_USAGE_COUNT,
                            CRITERION_MANUAL,
                        ]
                    )
                }
            ),
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        subentry = self._get_reconfigure_subentry()
        self._existing_data = dict(subentry.data)
        self._criterion = self._existing_data.get(CONF_CRITERION)
        return await self._async_show_details_step()

    async def async_step_time_elapsed(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        return await self._async_handle_details(CRITERION_TIME_ELAPSED, user_input)

    async def async_step_entity_on_duration(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        return await self._async_handle_details(CRITERION_ENTITY_ON_DURATION, user_input)

    async def async_step_entity_usage_count(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        return await self._async_handle_details(CRITERION_ENTITY_USAGE_COUNT, user_input)

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        return await self._async_handle_details(CRITERION_MANUAL, user_input)

    async def _async_show_details_step(self) -> SubentryFlowResult:
        assert self._criterion is not None
        return self._show_form(self._criterion)

    async def _async_handle_details(
        self, criterion: str, user_input: dict[str, Any] | None
    ) -> SubentryFlowResult:
        if user_input is None:
            return self._show_form(criterion)
        data: dict[str, Any] = {CONF_CRITERION: criterion, **user_input}
        title = data[CONF_NAME]
        if self.source == "reconfigure":
            return self.async_update_and_abort(
                self._get_reconfigure_entry(),
                self._get_reconfigure_subentry(),
                data=data,
                title=title,
            )
        return self.async_create_entry(title=title, data=data)

    def _show_form(self, criterion: str) -> SubentryFlowResult:
        schema = _CRITERION_SCHEMAS[criterion]
        suggested = {k: v for k, v in self._existing_data.items() if k != CONF_CRITERION}
        return self.async_show_form(
            step_id=criterion,
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
        )
