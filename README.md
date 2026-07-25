# Maintenance Tracker for Home Assistant

Custom integration that tracks recurring maintenance tasks and tells you when they're due.

Each **tracker** is one maintenance job (change oven filter, clean washer, replace HVAC filter). A tracker's state is one of `ok`, `due_soon`, `overdue`. Attributes expose the estimated due date, the current counter, progress toward the next due, and when it was last done.

## Criteria

| Criterion | When it becomes due |
|---|---|
| `time_elapsed` | The configured interval has passed since it was last done |
| `entity_on_duration` | A target entity has spent the configured duration in the "on" state since it was last done |
| `entity_usage_count` | A target entity has transitioned `from → to` state N times since it was last done |
| `manual` | Only marked via the "mark done" service / button |

Durations (interval / on-duration threshold) accept **minutes, hours, days, weeks, months, or years**. Months and years are computed as 30.4375 and 365.25 days respectively.

## Installation

**HACS (recommended):** add this repository as a custom integration in HACS, then install *Maintenance Tracker*.

**Manual:** copy `custom_components/maintenance` into your Home Assistant `config/custom_components/` directory.

Restart Home Assistant.

## Usage

1. **Settings → Devices & Services → Add integration → Maintenance**.
2. From the integration card, **Add tracker** and follow the flow to configure the criterion.
3. The new sensor `sensor.<tracker_name>` and companion `button.<tracker_name>_mark_done` become available.
4. To mark a task done, press the button, call the `maintenance.mark_done` service, or listen for the `maintenance_completed` event in automations.

## Sensor shape

```yaml
sensor.oven_cleaning:
  state: due_soon
  attributes:
    estimated_due_date: 2026-08-14T00:00:00+00:00
    counter: 435
    counter_unit: hours
    last_done_date: 2026-05-14T09:12:00+00:00
    progress: 87
    criterion: entity_on_duration
    threshold: 500
    warn_threshold_percent: 90
```

## Services

- `maintenance.mark_done` — mark target tracker(s) done. Optional `date` field (defaults to now).
- `maintenance.reset` — reset the counter without changing `last_done_date`.

## Events

`maintenance_completed` fires with `entity_id`, `tracker_id`, `date` whenever a tracker is marked done.
