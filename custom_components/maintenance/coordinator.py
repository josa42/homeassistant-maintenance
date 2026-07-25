"""Coordinators that compute a maintenance tracker's counter and state."""

from __future__ import annotations

from abc import abstractmethod
import calendar
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
import logging
from typing import Any

from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

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
    DEFAULT_WARN_THRESHOLD_PERCENT,
    DOMAIN,
    MONTH_ANY,
    STATE_DUE_SOON,
    STATE_OK,
    STATE_OVERDUE,
    UNIT_DAYS,
    UNIT_SECONDS,
    UNIT_USES,
)

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=1)


@dataclass
class MaintenanceData:
    """Snapshot of a tracker's computed state."""

    state: str
    counter: float
    counter_unit: str
    progress: float
    threshold: float
    last_done_date: datetime | None
    estimated_due_date: datetime | None
    criterion: str
    warn_threshold_percent: int

    def as_attributes(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("state")
        for key in ("last_done_date", "estimated_due_date"):
            if data[key] is not None:
                data[key] = data[key].isoformat()
        return data


@dataclass
class PersistedTracker:
    """What we save to disk for one tracker."""

    last_done_date: datetime | None = None
    accumulated_seconds: float = 0.0
    usage_count: int = 0
    on_since: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_done_date": self.last_done_date.isoformat() if self.last_done_date else None,
            "accumulated_seconds": self.accumulated_seconds,
            "usage_count": self.usage_count,
            "on_since": self.on_since.isoformat() if self.on_since else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> PersistedTracker:
        if not data:
            return cls()
        return cls(
            last_done_date=_parse_dt(data.get("last_done_date")),
            accumulated_seconds=float(data.get("accumulated_seconds") or 0.0),
            usage_count=int(data.get("usage_count") or 0),
            on_since=_parse_dt(data.get("on_since")),
        )


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    parsed = dt_util.parse_datetime(str(value))
    if parsed is None:
        return None
    return dt_util.as_utc(parsed)


class TrackerStore:
    """Wraps hass Store for all trackers under one integration entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, 1, f"{DOMAIN}.{entry_id}")
        self._data: dict[str, PersistedTracker] = {}

    async def async_load(self) -> None:
        raw = await self._store.async_load() or {}
        trackers = raw.get("trackers", {})
        self._data = {tid: PersistedTracker.from_dict(v) for tid, v in trackers.items()}

    def get(self, tracker_id: str) -> PersistedTracker:
        return self._data.setdefault(tracker_id, PersistedTracker())

    def drop(self, tracker_id: str) -> None:
        self._data.pop(tracker_id, None)
        self._schedule_save()

    async def async_save_now(self) -> None:
        await self._store.async_save(self._to_dict())

    def _schedule_save(self, delay: float = 1.0) -> None:
        self._store.async_delay_save(self._to_dict, delay)

    def _to_dict(self) -> dict[str, Any]:
        return {"trackers": {tid: t.to_dict() for tid, t in self._data.items()}}

    def mark_dirty(self) -> None:
        self._schedule_save()


class MaintenanceCoordinator(DataUpdateCoordinator[MaintenanceData]):
    """Base coordinator; one per tracker (subentry)."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        tracker_id: str,
        config: dict[str, Any],
        store: TrackerStore,
    ) -> None:
        self.entry_id = entry_id
        self.tracker_id = tracker_id
        self.config = config
        self.store = store
        self.name_conf: str = config[CONF_NAME]
        self.warn_threshold_percent: int = int(
            config.get(CONF_WARN_THRESHOLD_PERCENT, DEFAULT_WARN_THRESHOLD_PERCENT)
        )
        self._unsub_state: list = []
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}[{self.name_conf}]",
            update_interval=UPDATE_INTERVAL,
        )

    @property
    def persisted(self) -> PersistedTracker:
        return self.store.get(self.tracker_id)

    async def async_start(self) -> None:
        """Subclasses may attach listeners."""

    def async_stop(self) -> None:
        for unsub in self._unsub_state:
            unsub()
        self._unsub_state.clear()

    async def _async_update_data(self) -> MaintenanceData:
        return self._compute()

    @abstractmethod
    def _compute(self) -> MaintenanceData:
        raise NotImplementedError

    def _state_from_progress(self, progress: float) -> str:
        if progress >= 100:
            return STATE_OVERDUE
        if progress >= self.warn_threshold_percent:
            return STATE_DUE_SOON
        return STATE_OK

    async def async_mark_done(self, when: datetime | None = None) -> None:
        when = dt_util.as_utc(when) if when else dt_util.utcnow()
        persisted = self.persisted
        persisted.last_done_date = when
        persisted.accumulated_seconds = 0.0
        persisted.usage_count = 0
        persisted.on_since = None
        self.store.mark_dirty()
        self.hass.bus.async_fire(
            "maintenance_completed",
            {"tracker_id": self.tracker_id, "date": when.isoformat()},
        )
        await self.async_refresh()

    async def async_reset_counter(self) -> None:
        persisted = self.persisted
        persisted.accumulated_seconds = 0.0
        persisted.usage_count = 0
        persisted.on_since = None
        self.store.mark_dirty()
        await self.async_refresh()


class TimeElapsedCoordinator(MaintenanceCoordinator):
    """Due after a configured interval (value + unit) since last_done."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.interval_value: float = float(self.config[CONF_INTERVAL])
        self.interval_unit: str = self.config.get(CONF_INTERVAL_UNIT, DEFAULT_INTERVAL_UNIT)
        self.interval_seconds: float = self.interval_value * UNIT_SECONDS[self.interval_unit]

    def _compute(self) -> MaintenanceData:
        last_done = self.persisted.last_done_date
        now = dt_util.utcnow()
        elapsed_seconds = (now - last_done).total_seconds() if last_done else 0.0
        unit_seconds = UNIT_SECONDS[self.interval_unit]
        counter = elapsed_seconds / unit_seconds
        progress = (elapsed_seconds / self.interval_seconds * 100) if self.interval_seconds > 0 else 0.0
        due = last_done + timedelta(seconds=self.interval_seconds) if last_done else None
        return MaintenanceData(
            state=self._state_from_progress(progress),
            counter=round(counter, 2),
            counter_unit=self.interval_unit,
            progress=round(progress, 1),
            threshold=self.interval_value,
            last_done_date=last_done,
            estimated_due_date=due,
            criterion=CRITERION_TIME_ELAPSED,
            warn_threshold_percent=self.warn_threshold_percent,
        )


class EntityOnDurationCoordinator(MaintenanceCoordinator):
    """Accumulate seconds the target entity spends in the on-state."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.target_entity: str = self.config[CONF_TARGET_ENTITY]
        self.on_state: str = self.config.get(CONF_ON_STATE, DEFAULT_ON_STATE)
        self.threshold_value: float = float(self.config[CONF_THRESHOLD])
        self.threshold_unit: str = self.config.get(CONF_THRESHOLD_UNIT, DEFAULT_THRESHOLD_UNIT)
        self.threshold_seconds: float = self.threshold_value * UNIT_SECONDS[self.threshold_unit]

    async def async_start(self) -> None:
        self._sync_on_since()
        self._unsub_state.append(
            async_track_state_change_event(
                self.hass, [self.target_entity], self._on_state_change
            )
        )

    @callback
    def _sync_on_since(self) -> None:
        """Seed ``on_since`` from the current state.

        Called on startup, mark_done, and reset so a continuously-on entity's
        counter keeps advancing without waiting for an off→on transition.
        """
        current = self.hass.states.get(self.target_entity)
        is_on = current is not None and current.state == self.on_state
        persisted = self.persisted
        if is_on and persisted.on_since is None:
            persisted.on_since = dt_util.utcnow()
            self.store.mark_dirty()
        elif not is_on and persisted.on_since is not None:
            persisted.on_since = None
            self.store.mark_dirty()

    async def async_mark_done(self, when: datetime | None = None) -> None:
        await super().async_mark_done(when)
        self._sync_on_since()
        await self.async_refresh()

    async def async_reset_counter(self) -> None:
        await super().async_reset_counter()
        self._sync_on_since()
        await self.async_refresh()

    @callback
    def _on_state_change(self, event: Event[EventStateChangedData]) -> None:
        new_state = event.data["new_state"]
        old_state = event.data["old_state"]
        persisted = self.persisted
        now = dt_util.utcnow()
        was_on = old_state is not None and old_state.state == self.on_state
        is_on = new_state is not None and new_state.state == self.on_state
        if was_on and not is_on and persisted.on_since is not None:
            persisted.accumulated_seconds += (now - persisted.on_since).total_seconds()
            persisted.on_since = None
            self.store.mark_dirty()
        elif not was_on and is_on:
            persisted.on_since = now
            self.store.mark_dirty()
        self.hass.async_create_task(self.async_refresh())

    def _current_seconds(self) -> float:
        persisted = self.persisted
        seconds = persisted.accumulated_seconds
        if persisted.on_since is not None:
            seconds += (dt_util.utcnow() - persisted.on_since).total_seconds()
        return seconds

    def _compute(self) -> MaintenanceData:
        seconds = self._current_seconds()
        unit_seconds = UNIT_SECONDS[self.threshold_unit]
        counter = seconds / unit_seconds
        progress = (seconds / self.threshold_seconds * 100) if self.threshold_seconds > 0 else 0.0
        last_done = self.persisted.last_done_date
        due = self._estimate_due(seconds, last_done)
        return MaintenanceData(
            state=self._state_from_progress(progress),
            counter=round(counter, 2),
            counter_unit=self.threshold_unit,
            progress=round(progress, 1),
            threshold=self.threshold_value,
            last_done_date=last_done,
            estimated_due_date=due,
            criterion=CRITERION_ENTITY_ON_DURATION,
            warn_threshold_percent=self.warn_threshold_percent,
        )

    def _estimate_due(
        self, accumulated_seconds: float, last_done: datetime | None
    ) -> datetime | None:
        if last_done is None or accumulated_seconds <= 0:
            return None
        now = dt_util.utcnow()
        elapsed_seconds = (now - last_done).total_seconds()
        if elapsed_seconds <= 0:
            return None
        rate = accumulated_seconds / elapsed_seconds
        remaining = self.threshold_seconds - accumulated_seconds
        if rate <= 0:
            return None
        return now + timedelta(seconds=remaining / rate)


class EntityUsageCountCoordinator(MaintenanceCoordinator):
    """Count from_state → to_state transitions."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.target_entity: str = self.config[CONF_TARGET_ENTITY]
        self.from_state: str = self.config.get(CONF_FROM_STATE, DEFAULT_FROM_STATE)
        self.to_state: str = self.config.get(CONF_TO_STATE, DEFAULT_TO_STATE)
        self.threshold_count: int = int(self.config[CONF_THRESHOLD_COUNT])

    async def async_start(self) -> None:
        self._unsub_state.append(
            async_track_state_change_event(
                self.hass, [self.target_entity], self._on_state_change
            )
        )

    @callback
    def _on_state_change(self, event: Event[EventStateChangedData]) -> None:
        new_state = event.data["new_state"]
        old_state = event.data["old_state"]
        if new_state is None or old_state is None:
            return
        if old_state.state == self.from_state and new_state.state == self.to_state:
            self.persisted.usage_count += 1
            self.store.mark_dirty()
            self.hass.async_create_task(self.async_refresh())

    def _compute(self) -> MaintenanceData:
        count = self.persisted.usage_count
        progress = (count / self.threshold_count * 100) if self.threshold_count > 0 else 0.0
        last_done = self.persisted.last_done_date
        due = self._estimate_due(count, last_done)
        return MaintenanceData(
            state=self._state_from_progress(progress),
            counter=count,
            counter_unit=UNIT_USES,
            progress=round(progress, 1),
            threshold=self.threshold_count,
            last_done_date=last_done,
            estimated_due_date=due,
            criterion=CRITERION_ENTITY_USAGE_COUNT,
            warn_threshold_percent=self.warn_threshold_percent,
        )

    def _estimate_due(self, count: int, last_done: datetime | None) -> datetime | None:
        if last_done is None or count <= 0:
            return None
        now = dt_util.utcnow()
        elapsed_seconds = (now - last_done).total_seconds()
        if elapsed_seconds <= 0:
            return None
        rate = count / elapsed_seconds
        remaining = self.threshold_count - count
        if rate <= 0:
            return None
        return now + timedelta(seconds=remaining / rate)


class RecurringDateCoordinator(MaintenanceCoordinator):
    """Due on a recurring calendar date (every Nth of month, or every Nth of MonthName)."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.day: int = int(self.config[CONF_DAY_OF_MONTH])
        raw_month = self.config.get(CONF_MONTH_OF_YEAR)
        if raw_month in (None, MONTH_ANY, "", 0):
            self.month: int | None = None
        else:
            self.month = int(raw_month)

    @staticmethod
    def _clamp_date(year: int, month: int, day: int) -> date:
        """Clamp day to the last valid day of the month (e.g. Feb 30 → Feb 28/29)."""
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, min(day, last_day))

    def _to_dt(self, d: date, tz) -> datetime:
        return datetime.combine(d, datetime.min.time(), tzinfo=tz)

    def _next_occurrence(self, after: datetime) -> datetime:
        """Return the next scheduled datetime strictly after ``after``."""
        after_date = after.date()
        if self.month is not None:
            candidate = self._clamp_date(after_date.year, self.month, self.day)
            if candidate <= after_date:
                candidate = self._clamp_date(after_date.year + 1, self.month, self.day)
        else:
            year, month = after_date.year, after_date.month
            candidate = self._clamp_date(year, month, self.day)
            if candidate <= after_date:
                month += 1
                if month > 12:
                    month = 1
                    year += 1
                candidate = self._clamp_date(year, month, self.day)
        return self._to_dt(candidate, after.tzinfo)

    def _prev_occurrence(self, at_or_before: datetime) -> datetime:
        """Return the most recent scheduled datetime ≤ ``at_or_before``."""
        d = at_or_before.date()
        if self.month is not None:
            candidate = self._clamp_date(d.year, self.month, self.day)
            candidate_dt = self._to_dt(candidate, at_or_before.tzinfo)
            if candidate_dt > at_or_before:
                candidate = self._clamp_date(d.year - 1, self.month, self.day)
                candidate_dt = self._to_dt(candidate, at_or_before.tzinfo)
            return candidate_dt
        year, month = d.year, d.month
        candidate = self._clamp_date(year, month, self.day)
        candidate_dt = self._to_dt(candidate, at_or_before.tzinfo)
        if candidate_dt > at_or_before:
            month -= 1
            if month < 1:
                month = 12
                year -= 1
            candidate = self._clamp_date(year, month, self.day)
            candidate_dt = self._to_dt(candidate, at_or_before.tzinfo)
        return candidate_dt

    def _compute(self) -> MaintenanceData:
        now = dt_util.utcnow()
        prev_due = self._prev_occurrence(now)
        next_due = self._next_occurrence(now)

        interval_sec = (next_due - prev_due).total_seconds()
        elapsed_sec = (now - prev_due).total_seconds()
        progress = (elapsed_sec / interval_sec * 100) if interval_sec > 0 else 0.0
        counter_days = elapsed_sec / 86400
        threshold_days = interval_sec / 86400

        last_done = self.persisted.last_done_date
        # Overdue if we haven't done the task since the previous scheduled date.
        if last_done is None or last_done < prev_due:
            state = STATE_OVERDUE
        else:
            state = self._state_from_progress(progress)

        return MaintenanceData(
            state=state,
            counter=round(counter_days, 2),
            counter_unit=UNIT_DAYS,
            progress=round(progress, 1),
            threshold=round(threshold_days, 2),
            last_done_date=last_done,
            estimated_due_date=next_due,
            criterion=CRITERION_RECURRING_DATE,
            warn_threshold_percent=self.warn_threshold_percent,
        )


def build_coordinator(
    hass: HomeAssistant,
    entry_id: str,
    tracker_id: str,
    config: dict[str, Any],
    store: TrackerStore,
) -> MaintenanceCoordinator:
    """Return the right coordinator for the criterion in ``config``."""
    criterion = config[CONF_CRITERION]
    if criterion == CRITERION_TIME_ELAPSED:
        return TimeElapsedCoordinator(hass, entry_id, tracker_id, config, store)
    if criterion == CRITERION_ENTITY_ON_DURATION:
        return EntityOnDurationCoordinator(hass, entry_id, tracker_id, config, store)
    if criterion == CRITERION_ENTITY_USAGE_COUNT:
        return EntityUsageCountCoordinator(hass, entry_id, tracker_id, config, store)
    if criterion == CRITERION_RECURRING_DATE:
        return RecurringDateCoordinator(hass, entry_id, tracker_id, config, store)
    raise ValueError(f"Unknown criterion: {criterion}")
