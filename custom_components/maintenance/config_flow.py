"""Config flow for the Maintenance integration.

Each tracker is its own config entry — the idiomatic pattern for helpers.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CRITERION,
    CONF_DAY_OF_MONTH,
    CONF_FROM_STATE,
    CONF_INTERVAL,
    CONF_INTERVAL_UNIT,
    CONF_MONTH_OF_YEAR,
    CONF_NAME,
    CONF_ON_STATE,
    CONF_TARGET_ENTITY,
    CONF_THRESHOLD,
    CONF_THRESHOLD_COUNT,
    CONF_THRESHOLD_UNIT,
    CONF_TO_STATE,
    CONF_WARN_DAYS_BEFORE,
    CONF_WARN_THRESHOLD_PERCENT,
    CRITERION_ENTITY_ON_DURATION,
    CRITERION_ENTITY_USAGE_COUNT,
    CRITERION_RECURRING_DATE,
    CRITERION_TIME_ELAPSED,
    DEFAULT_FROM_STATE,
    DEFAULT_INTERVAL_UNIT,
    DEFAULT_ON_STATE,
    DEFAULT_THRESHOLD_UNIT,
    DEFAULT_TO_STATE,
    DEFAULT_WARN_DAYS_BEFORE,
    DEFAULT_WARN_THRESHOLD_PERCENT,
    DOMAIN,
    DURATION_UNITS,
    MONTH_ANY,
)

_WARN_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(min=1, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
)
_NAME_SELECTOR = selector.TextSelector()
_ENTITY_SELECTOR = selector.EntitySelector()
_TEXT_SELECTOR = selector.TextSelector()
_DURATION_UNIT_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=list(DURATION_UNITS),
        translation_key="duration_unit",
        mode=selector.SelectSelectorMode.DROPDOWN,
    )
)

_CRITERION_SCHEMAS: dict[str, vol.Schema] = {
    CRITERION_TIME_ELAPSED: vol.Schema(
        {
            vol.Required(CONF_NAME): _NAME_SELECTOR,
            vol.Required(CONF_INTERVAL): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(CONF_INTERVAL_UNIT, default=DEFAULT_INTERVAL_UNIT): _DURATION_UNIT_SELECTOR,
            vol.Required(CONF_WARN_THRESHOLD_PERCENT, default=DEFAULT_WARN_THRESHOLD_PERCENT): _WARN_SELECTOR,
        }
    ),
    CRITERION_ENTITY_ON_DURATION: vol.Schema(
        {
            vol.Required(CONF_NAME): _NAME_SELECTOR,
            vol.Required(CONF_TARGET_ENTITY): _ENTITY_SELECTOR,
            vol.Required(CONF_ON_STATE, default=DEFAULT_ON_STATE): _TEXT_SELECTOR,
            vol.Required(CONF_THRESHOLD): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0.5, step=0.5, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(CONF_THRESHOLD_UNIT, default=DEFAULT_THRESHOLD_UNIT): _DURATION_UNIT_SELECTOR,
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
    CRITERION_RECURRING_DATE: vol.Schema(
        {
            vol.Required(CONF_NAME): _NAME_SELECTOR,
            vol.Required(CONF_DAY_OF_MONTH): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=31, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(CONF_MONTH_OF_YEAR, default=MONTH_ANY): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        MONTH_ANY,
                        "1", "2", "3", "4", "5", "6",
                        "7", "8", "9", "10", "11", "12",
                    ],
                    translation_key="month_of_year",
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(CONF_WARN_DAYS_BEFORE, default=DEFAULT_WARN_DAYS_BEFORE): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
        }
    ),
}


class MaintenanceConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create one maintenance tracker per config entry."""

    VERSION = 2

    def __init__(self) -> None:
        self._criterion: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MaintenanceOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._criterion = user_input[CONF_CRITERION]
            return await self._async_show_details_step()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CRITERION, default=CRITERION_TIME_ELAPSED): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                CRITERION_TIME_ELAPSED,
                                CRITERION_ENTITY_ON_DURATION,
                                CRITERION_ENTITY_USAGE_COUNT,
                                CRITERION_RECURRING_DATE,
                            ],
                            translation_key="criterion",
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        self._criterion = entry.data.get(CONF_CRITERION)
        return await self._async_show_details_step(existing_data=dict(entry.data))

    async def async_step_time_elapsed(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_handle_details(CRITERION_TIME_ELAPSED, user_input)

    async def async_step_entity_on_duration(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_handle_details(CRITERION_ENTITY_ON_DURATION, user_input)

    async def async_step_entity_usage_count(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_handle_details(CRITERION_ENTITY_USAGE_COUNT, user_input)

    async def async_step_recurring_date(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_handle_details(CRITERION_RECURRING_DATE, user_input)

    async def _async_show_details_step(
        self, existing_data: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._criterion is not None
        return self._show_form(self._criterion, existing_data or {})

    async def _async_handle_details(
        self, criterion: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        if user_input is None:
            return self._show_form(criterion, {})
        data: dict[str, Any] = {CONF_CRITERION: criterion, **user_input}
        title = data[CONF_NAME]
        if self.source == "reconfigure":
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(), data=data, title=title
            )
        return self.async_create_entry(title=title, data=data)

    def _show_form(self, criterion: str, existing_data: dict[str, Any]) -> ConfigFlowResult:
        schema = _CRITERION_SCHEMAS[criterion]
        suggested = {k: v for k, v in existing_data.items() if k != CONF_CRITERION}
        return self.async_show_form(
            step_id=criterion,
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
        )


class MaintenanceOptionsFlow(OptionsFlow):
    """Edit an existing tracker.

    Shown as the "Configure" button on the helper card. The criterion cannot be
    changed here (the persisted counter depends on it) — delete and recreate the
    tracker if you need a different criterion.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self.config_entry
        criterion = entry.data[CONF_CRITERION]
        schema = _CRITERION_SCHEMAS[criterion]

        if user_input is not None:
            new_data = {CONF_CRITERION: criterion, **user_input}
            self.hass.config_entries.async_update_entry(
                entry, data=new_data, title=user_input[CONF_NAME]
            )
            return self.async_create_entry(title="", data={})

        suggested = {k: v for k, v in entry.data.items() if k != CONF_CRITERION}
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
        )
