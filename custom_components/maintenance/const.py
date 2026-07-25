"""Constants for the Maintenance integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "maintenance"

PLATFORMS: Final = ["sensor", "button"]

# Criterion identifiers
CRITERION_TIME_ELAPSED: Final = "time_elapsed"
CRITERION_ENTITY_ON_DURATION: Final = "entity_on_duration"
CRITERION_ENTITY_USAGE_COUNT: Final = "entity_usage_count"
CRITERION_RECURRING_DATE: Final = "recurring_date"

CRITERIA: Final = (
    CRITERION_TIME_ELAPSED,
    CRITERION_ENTITY_ON_DURATION,
    CRITERION_ENTITY_USAGE_COUNT,
    CRITERION_RECURRING_DATE,
)

# Tracker states
STATE_OK: Final = "ok"
STATE_DUE_SOON: Final = "due_soon"
STATE_OVERDUE: Final = "overdue"

# Duration units (used for interval + on-duration threshold)
UNIT_MINUTES: Final = "minutes"
UNIT_HOURS: Final = "hours"
UNIT_DAYS: Final = "days"
UNIT_WEEKS: Final = "weeks"
UNIT_MONTHS: Final = "months"
UNIT_YEARS: Final = "years"

DURATION_UNITS: Final = (
    UNIT_MINUTES,
    UNIT_HOURS,
    UNIT_DAYS,
    UNIT_WEEKS,
    UNIT_MONTHS,
    UNIT_YEARS,
)

# Seconds per configured unit. Months and years use average lengths (30.4375 / 365.25 days)
# because trackers are approximate — a month-old task doesn't care whether the month
# was 28 or 31 days.
UNIT_SECONDS: Final[dict[str, float]] = {
    UNIT_MINUTES: 60.0,
    UNIT_HOURS: 3600.0,
    UNIT_DAYS: 86400.0,
    UNIT_WEEKS: 604800.0,
    UNIT_MONTHS: 2629800.0,
    UNIT_YEARS: 31557600.0,
}

# Non-duration counter unit (for entity_usage_count)
UNIT_USES: Final = "uses"

# Configuration keys
CONF_NAME: Final = "name"
CONF_CRITERION: Final = "criterion"
CONF_INTERVAL: Final = "interval"
CONF_INTERVAL_UNIT: Final = "interval_unit"
CONF_TARGET_ENTITY: Final = "target_entity_id"
CONF_ON_STATE: Final = "on_state"
CONF_FROM_STATE: Final = "from_state"
CONF_TO_STATE: Final = "to_state"
CONF_THRESHOLD: Final = "threshold"
CONF_THRESHOLD_UNIT: Final = "threshold_unit"
CONF_THRESHOLD_COUNT: Final = "threshold_count"
CONF_WARN_THRESHOLD_PERCENT: Final = "warn_threshold_percent"
CONF_DAY_OF_MONTH: Final = "day_of_month"
CONF_MONTH_OF_YEAR: Final = "month_of_year"
CONF_WARN_DAYS_BEFORE: Final = "warn_days_before"

MONTH_ANY: Final = "any"

DEFAULT_WARN_DAYS_BEFORE: Final = 3

DEFAULT_WARN_THRESHOLD_PERCENT: Final = 90
DEFAULT_ON_STATE: Final = "on"
DEFAULT_FROM_STATE: Final = "off"
DEFAULT_TO_STATE: Final = "on"
DEFAULT_INTERVAL_UNIT: Final = UNIT_DAYS
DEFAULT_THRESHOLD_UNIT: Final = UNIT_HOURS

EVENT_MAINTENANCE_COMPLETED: Final = "maintenance_completed"

SERVICE_MARK_DONE: Final = "mark_done"
SERVICE_RESET: Final = "reset"

STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = "maintenance_trackers"
