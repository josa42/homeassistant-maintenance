"""Constants for the Maintenance integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "maintenance"

PLATFORMS: Final = ["sensor", "button"]

# Criterion identifiers
CRITERION_TIME_ELAPSED: Final = "time_elapsed"
CRITERION_ENTITY_ON_DURATION: Final = "entity_on_duration"
CRITERION_ENTITY_USAGE_COUNT: Final = "entity_usage_count"
CRITERION_MANUAL: Final = "manual"

CRITERIA: Final = (
    CRITERION_TIME_ELAPSED,
    CRITERION_ENTITY_ON_DURATION,
    CRITERION_ENTITY_USAGE_COUNT,
    CRITERION_MANUAL,
)

# Tracker states
STATE_OK: Final = "ok"
STATE_DUE_SOON: Final = "due_soon"
STATE_OVERDUE: Final = "overdue"

# Counter units
UNIT_DAYS: Final = "d"
UNIT_HOURS: Final = "h"
UNIT_USES: Final = "uses"

# Configuration keys
CONF_NAME: Final = "name"
CONF_CRITERION: Final = "criterion"
CONF_INTERVAL_DAYS: Final = "interval_days"
CONF_TARGET_ENTITY: Final = "target_entity_id"
CONF_ON_STATE: Final = "on_state"
CONF_FROM_STATE: Final = "from_state"
CONF_TO_STATE: Final = "to_state"
CONF_THRESHOLD_HOURS: Final = "threshold_hours"
CONF_THRESHOLD_COUNT: Final = "threshold_count"
CONF_WARN_THRESHOLD_PERCENT: Final = "warn_threshold_percent"

DEFAULT_WARN_THRESHOLD_PERCENT: Final = 90
DEFAULT_ON_STATE: Final = "on"
DEFAULT_FROM_STATE: Final = "off"
DEFAULT_TO_STATE: Final = "on"

EVENT_MAINTENANCE_COMPLETED: Final = "maintenance_completed"

SERVICE_MARK_DONE: Final = "mark_done"
SERVICE_RESET: Final = "reset"

STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = "maintenance_trackers"
