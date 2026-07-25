"""Coordinators that compute a maintenance tracker's counter and state."""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

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
    STATE_DUE_SOON,
    STATE_OK,
    STATE_OVERDUE,
    UNIT_DAYS,
    UNIT_HOURS,
    UNIT_USES,
)

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=1)
DURATION_TICK_INTERVAL = timedelta(minutes=5)


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
    """Due after N days since last_done."""

    def _compute(self) -> MaintenanceData:
        interval_days = float(self.config[CONF_INTERVAL_DAYS])
        last_done = self.persisted.last_done_date
        now = dt_util.utcnow()
        elapsed_days = (now - last_done).total_seconds() / 86400 if last_done else 0.0
        progress = (elapsed_days / interval_days * 100) if interval_days > 0 else 0.0
        due = last_done + timedelta(days=interval_days) if last_done else None
        return MaintenanceData(
            state=self._state_from_progress(progress),
            counter=round(elapsed_days, 2),
            counter_unit=UNIT_DAYS,
            progress=round(progress, 1),
            threshold=interval_days,
            last_done_date=last_done,
            estimated_due_date=due,
            criterion=CRITERION_TIME_ELAPSED,
            warn_threshold_percent=self.warn_threshold_percent,
        )


class ManualCoordinator(MaintenanceCoordinator):
    """No auto-trigger; state is always ok until manually overdue."""

    def _compute(self) -> MaintenanceData:
        last_done = self.persisted.last_done_date
        now = dt_util.utcnow()
        elapsed_days = (now - last_done).total_seconds() / 86400 if last_done else 0.0
        return MaintenanceData(
            state=STATE_OK,
            counter=round(elapsed_days, 2),
            counter_unit=UNIT_DAYS,
            progress=0.0,
            threshold=0.0,
            last_done_date=last_done,
            estimated_due_date=None,
            criterion=CRITERION_MANUAL,
            warn_threshold_percent=self.warn_threshold_percent,
        )


class EntityOnDurationCoordinator(MaintenanceCoordinator):
    """Accumulate seconds the target entity spends in the on-state."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.target_entity: str = self.config[CONF_TARGET_ENTITY]
        self.on_state: str = self.config.get(CONF_ON_STATE, DEFAULT_ON_STATE)
        self.threshold_hours: float = float(self.config[CONF_THRESHOLD_HOURS])

    async def async_start(self) -> None:
        # If HA restarted while the entity was on, we do not know how long
        # it has been on since restart. Seed on_since from current state.
        current = self.hass.states.get(self.target_entity)
        if current is not None and current.state == self.on_state:
            self.persisted.on_since = dt_util.utcnow()
            self.store.mark_dirty()
        self._unsub_state.append(
            async_track_state_change_event(
                self.hass, [self.target_entity], self._on_state_change
            )
        )
        # Tick regularly so the counter advances while the entity remains on.
        self.update_interval = DURATION_TICK_INTERVAL

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
        hours = seconds / 3600
        progress = (hours / self.threshold_hours * 100) if self.threshold_hours > 0 else 0.0
        last_done = self.persisted.last_done_date
        due = self._estimate_due(hours, last_done)
        return MaintenanceData(
            state=self._state_from_progress(progress),
            counter=round(hours, 2),
            counter_unit=UNIT_HOURS,
            progress=round(progress, 1),
            threshold=self.threshold_hours,
            last_done_date=last_done,
            estimated_due_date=due,
            criterion=CRITERION_ENTITY_ON_DURATION,
            warn_threshold_percent=self.warn_threshold_percent,
        )

    def _estimate_due(self, hours: float, last_done: datetime | None) -> datetime | None:
        if last_done is None or hours <= 0:
            return None
        now = dt_util.utcnow()
        elapsed_seconds = (now - last_done).total_seconds()
        if elapsed_seconds <= 0:
            return None
        rate_hours_per_sec = hours / elapsed_seconds
        remaining_hours = self.threshold_hours - hours
        if rate_hours_per_sec <= 0:
            return None
        remaining_seconds = remaining_hours / rate_hours_per_sec
        return now + timedelta(seconds=remaining_seconds)


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
    if criterion == CRITERION_MANUAL:
        return ManualCoordinator(hass, entry_id, tracker_id, config, store)
    raise ValueError(f"Unknown criterion: {criterion}")
