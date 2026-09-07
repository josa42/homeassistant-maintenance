const CARD_VERSION = "1.0.0";

const STATE_COLOR = {
  ok: "var(--success-color, #4caf50)",
  due_soon: "var(--warning-color, #ff9800)",
  overdue: "var(--error-color, #f44336)",
};

const STATE_ICON = {
  ok: "mdi:check-circle-outline",
  due_soon: "mdi:clock-outline",
  overdue: "mdi:alert-circle-outline",
};

const SECONDS_PER_UNIT = {
  minutes: 60,
  hours: 3600,
  days: 86400,
  weeks: 604800,
  months: 2629800,
  years: 31557600,
};

const EN_FALLBACK = {
  "component.maintenance.card.confirm_title": "Maintenance",
  "component.maintenance.card.confirm_body": 'Mark "{name}" as done?',
  "component.maintenance.card.confirm_ok": "Mark done",
  "component.maintenance.card.confirm_cancel": "Cancel",
  "component.maintenance.card.mark_done_action": "Mark done",
  "component.maintenance.card.empty_no_trackers":
    "No maintenance trackers configured.",
  "component.maintenance.card.empty_all_ok_one":
    "Nothing due — 1 tracker is up to date.",
  "component.maintenance.card.empty_all_ok_other":
    "Nothing due — all {count} trackers are up to date.",
  "component.maintenance.card.units.uses_one": "use",
  "component.maintenance.card.units.uses_other": "uses",
  "component.maintenance.card.editor.entity": "Maintenance tracker",
  "component.maintenance.card.editor.confirm": "Confirm before mark done",
  "component.maintenance.card.editor.hide_ok": "Hide OK trackers",
  "component.maintenance.card.editor.hide_when_empty": "Hide card when empty",
  "component.maintenance.card.editor.separate_items":
    "Render each item as its own card",
  "component.maintenance.entity.sensor.tracker.state.ok": "OK",
  "component.maintenance.entity.sensor.tracker.state.due_soon": "Due soon",
  "component.maintenance.entity.sensor.tracker.state.overdue": "Overdue",
};

function _t(hass, key, params) {
  const raw =
    (hass && hass.localize && hass.localize(key)) || EN_FALLBACK[key] || key;
  if (!params) return raw;
  return raw.replace(/\{(\w+)\}/g, (_, k) =>
    params[k] != null ? String(params[k]) : ""
  );
}

// Locale-aware duration display. Whole values in the configured unit render
// as a spelled-out unit ("2 minutes", "30 days"). Fractional minute/hour
// counters render as M:SS / H:MM digital format; fractional day+ counters
// render as two-component narrow-unit text like "3d 12h" ("3 T 12h" in DE).
function _fmtDuration(hass, value, unit) {
  const lang = (hass && hass.language) || "en";
  const nfInt = new Intl.NumberFormat(lang, { maximumFractionDigits: 0 });

  if (unit === "uses") {
    const rounded = Math.round(value);
    const key =
      rounded === 1
        ? "component.maintenance.card.units.uses_one"
        : "component.maintenance.card.units.uses_other";
    return `${nfInt.format(rounded)} ${_t(hass, key)}`;
  }

  if (!SECONDS_PER_UNIT[unit]) return nfInt.format(value);

  const unitSingular = {
    minutes: "minute",
    hours: "hour",
    days: "day",
    weeks: "week",
    months: "month",
    years: "year",
  }[unit];
  const fmtLong = (n, u) =>
    new Intl.NumberFormat(lang, {
      style: "unit",
      unit: u,
      unitDisplay: "long",
      maximumFractionDigits: 0,
    }).format(n);
  const fmtNarrow = (n, u) =>
    new Intl.NumberFormat(lang, {
      style: "unit",
      unit: u,
      unitDisplay: "narrow",
      maximumFractionDigits: 0,
    }).format(n);

  // Whole value in the configured unit → spelled-out unit label
  // (e.g. "2 minutes" / "2 Minuten" instead of "2:00").
  const rounded = Math.round(value);
  if (Math.abs(value - rounded) < 0.005) {
    return fmtLong(rounded, unitSingular);
  }

  const totalSec = value * SECONDS_PER_UNIT[unit];

  if (unit === "minutes") {
    const m = Math.floor(totalSec / 60);
    const s = Math.floor(totalSec % 60);
    return `${nfInt.format(m)}:${String(s).padStart(2, "0")}`;
  }
  if (unit === "hours") {
    const h = Math.floor(totalSec / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    return `${nfInt.format(h)}:${String(m).padStart(2, "0")}`;
  }

  const layouts = {
    days: [["day", 86400], ["hour", 3600]],
    weeks: [["week", 604800], ["day", 86400]],
    months: [["month", 2629800], ["day", 86400]],
    years: [["year", 31557600], ["month", 2629800]],
  };
  const [primary, secondary] = layouts[unit];
  const primaryVal = Math.floor(totalSec / primary[1]);
  const secondaryVal = Math.floor((totalSec - primaryVal * primary[1]) / secondary[1]);
  const parts = [];
  if (primaryVal > 0) parts.push(fmtNarrow(primaryVal, primary[0]));
  if (secondaryVal > 0) parts.push(fmtNarrow(secondaryVal, secondary[0]));
  if (parts.length === 0) parts.push(fmtNarrow(0, primary[0]));
  return parts.join(" ");
}

// Format "counter / threshold" and, when both values are whole numbers of the
// same unit, collapse the shared unit label to the end: "0 / 5 months" rather
// than "0 months / 5 months". Pluralisation always follows the threshold
// count (via Intl for standard units, via singular/plural translations for
// custom units like "uses").
function _fmtProgress(hass, counter, threshold, unit) {
  if (!Number.isFinite(counter)) return "";
  if (!threshold) return _fmtDuration(hass, counter, unit);

  const lang = (hass && hass.language) || "en";
  const cRounded = Math.round(counter);
  const tRounded = Math.round(threshold);
  const bothWhole =
    Math.abs(counter - cRounded) < 0.005 &&
    Math.abs(threshold - tRounded) < 0.005;

  if (bothWhole && SECONDS_PER_UNIT[unit]) {
    const unitSingular = {
      minutes: "minute", hours: "hour", days: "day",
      weeks: "week", months: "month", years: "year",
    }[unit];
    const nf = new Intl.NumberFormat(lang, { maximumFractionDigits: 0 });
    const thresholdWithUnit = new Intl.NumberFormat(lang, {
      style: "unit",
      unit: unitSingular,
      unitDisplay: "long",
      maximumFractionDigits: 0,
    }).format(tRounded);
    return `${nf.format(cRounded)} / ${thresholdWithUnit}`;
  }

  if (bothWhole && unit === "uses") {
    const nf = new Intl.NumberFormat(lang, { maximumFractionDigits: 0 });
    const key =
      tRounded === 1
        ? "component.maintenance.card.units.uses_one"
        : "component.maintenance.card.units.uses_other";
    return `${nf.format(cRounded)} / ${nf.format(tRounded)} ${_t(hass, key)}`;
  }

  return `${_fmtDuration(hass, counter, unit)} / ${_fmtDuration(hass, threshold, unit)}`;
}

function _stateLabelOf(hass, status) {
  return _t(hass, `component.maintenance.entity.sensor.tracker.state.${status}`);
}

function _relativeDueText(hass, dueIso, status) {
  if (!dueIso) return _stateLabelOf(hass, status);
  const due = new Date(dueIso);
  if (isNaN(due.getTime())) return _stateLabelOf(hass, status);
  const diffSec = (due.getTime() - Date.now()) / 1000;
  if (diffSec <= 0 && status !== "overdue") return _stateLabelOf(hass, status);
  if (diffSec > 0 && status === "overdue") return _stateLabelOf(hass, status);
  const abs = Math.abs(diffSec);
  let value, unit;
  if (abs < 60) { value = diffSec; unit = "second"; }
  else if (abs < 3600) { value = diffSec / 60; unit = "minute"; }
  else if (abs < 86400) { value = diffSec / 3600; unit = "hour"; }
  else if (abs < 2592000) { value = diffSec / 86400; unit = "day"; }
  else if (abs < 31536000) { value = diffSec / 2592000; unit = "month"; }
  else { value = diffSec / 31557600; unit = "year"; }
  const lang = (hass && hass.language) || "en";
  const rtf = new Intl.RelativeTimeFormat(lang, { numeric: "auto" });
  return rtf.format(Math.round(value), unit);
}

class MaintenanceCard extends HTMLElement {
  static getStubConfig() {
    return { entity: "" };
  }

  static async getConfigElement() {
    await customElements.whenDefined("maintenance-card-editor");
    return document.createElement("maintenance-card-editor");
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("You need to define an entity");
    }
    this._config = config;
    if (this._hass) this._update();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._config) this._update();
  }

  getCardSize() {
    return 1;
  }

  getLayoutOptions() {
    return {
      grid_columns: 2,
      grid_rows: 1,
      grid_min_columns: 2,
      grid_min_rows: 1,
      grid_max_rows: 2,
    };
  }

  connectedCallback() {
    if (this._config && this._hass) this._update();
  }

  disconnectedCallback() {
    if (this._tickHandle) {
      clearTimeout(this._tickHandle);
      this._tickHandle = null;
    }
  }

  _update() {
    const state = this._hass.states[this._config.entity];
    if (!state) {
      this._renderError(`Entity ${this._config.entity} not found`);
      return;
    }
    if (state.attributes.criterion === undefined) {
      this._renderError(`${this._config.entity} is not a maintenance tracker`);
      return;
    }
    this._render(state);
  }

  _render(state) {
    if (!this._built) this._build();

    const attrs = state.attributes;
    const status = state.state;
    const color = STATE_COLOR[status] || "var(--state-inactive-color)";
    const name = attrs.friendly_name || this._config.entity;
    const progress = Math.max(0, Math.min(100, Number(attrs.progress) || 0));
    const counter = Number(attrs.counter) || 0;
    const threshold = Number(attrs.threshold) || 0;
    const unit = attrs.counter_unit || "";
    const icon = this._config.icon || STATE_ICON[status] || "mdi:wrench-clock";

    this.style.setProperty("--state-color", color);
    this._els.name.textContent = name;
    this._els.due.textContent = _relativeDueText(
      this._hass,
      attrs.estimated_due_date,
      status
    );
    this._els.counter.textContent = _fmtProgress(
      this._hass,
      counter,
      threshold,
      unit
    );
    this._els.fill.style.width = `${progress}%`;
    this._els.icon.setAttribute("icon", icon);

    this._scheduleTick(attrs.estimated_due_date);
  }

  _scheduleTick(dueIso) {
    if (this._tickHandle) {
      clearTimeout(this._tickHandle);
      this._tickHandle = null;
    }
    if (!dueIso || !this.isConnected) return;
    const diffSec = Math.abs((new Date(dueIso).getTime() - Date.now()) / 1000);
    let ms;
    if (diffSec < 60) ms = 1000;
    else if (diffSec < 3600) ms = 30_000;
    else if (diffSec < 86400) ms = 300_000;
    else ms = 3_600_000;
    this._tickHandle = setTimeout(() => this._tick(), ms);
  }

  _tick() {
    if (!this.isConnected || !this._hass || !this._config) return;
    const state = this._hass.states[this._config.entity];
    if (!state || !this._built) return;
    this._els.due.textContent = _relativeDueText(
      this._hass,
      state.attributes.estimated_due_date,
      state.state
    );
    this._scheduleTick(state.attributes.estimated_due_date);
  }

  _build() {
    this.innerHTML = `
      <ha-card>
        <div class="tile" role="button" tabindex="0">
          <div class="icon-container">
            <div class="icon-bg"></div>
            <ha-icon></ha-icon>
          </div>
          <div class="info">
            <div class="row">
              <span class="name"></span>
              <span class="due"></span>
            </div>
            <div class="row bar-row">
              <div class="progress-bar"><div class="progress-fill"></div></div>
              <span class="counter"></span>
            </div>
          </div>
        </div>
        <style>
          :host { display: block; }
          ha-card {
            padding: 8px 16px;
            cursor: pointer;
            box-sizing: border-box;
            height: 100%;
            display: flex;
            align-items: center;
          }
          .tile { display: flex; align-items: center; gap: 12px; min-width: 0; width: 100%; }
          .icon-container {
            position: relative; width: 34px; height: 34px; flex-shrink: 0;
            display: flex; align-items: center; justify-content: center;
            cursor: pointer; border-radius: 50%;
          }
          .icon-container:hover .icon-bg { opacity: 0.35; }
          .icon-container:focus { outline: none; }
          .icon-container:focus-visible {
            outline: none;
            box-shadow: 0 0 0 2px var(--state-color);
          }
          .icon-bg {
            position: absolute; inset: 0; border-radius: 50%;
            background: var(--state-color); opacity: 0.2;
          }
          ha-icon {
            position: relative; color: var(--state-color); --mdc-icon-size: 22px;
          }
          .info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
          .row {
            display: flex; align-items: center; justify-content: space-between;
            gap: 8px; min-width: 0;
          }
          .name {
            font-weight: 500; color: var(--primary-text-color); font-size: 0.95em;
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap; line-height: 1.2;
          }
          .due, .counter {
            color: var(--secondary-text-color); font-size: 0.78em; line-height: 1.2;
            white-space: nowrap; flex-shrink: 0;
          }
          .progress-bar {
            flex: 1; height: 4px; background: var(--divider-color);
            border-radius: 2px; overflow: hidden; min-width: 30px;
          }
          .progress-fill {
            height: 100%; border-radius: 2px; background: var(--state-color);
            transition: width 0.3s ease, background 0.3s ease;
          }
          .tile:focus { outline: none; }
          .tile:focus-visible { outline: none; }
          /* Focus outline lives on ha-card so the whole card outlines,
             matching HA's own tile card behavior. */
          ha-card:has(.tile:focus-visible) {
            outline: 2px solid var(--state-color);
            outline-offset: 2px;
          }
        </style>
      </ha-card>
    `;
    this._els = {
      icon: this.querySelector("ha-icon"),
      name: this.querySelector(".name"),
      due: this.querySelector(".due"),
      counter: this.querySelector(".counter"),
      fill: this.querySelector(".progress-fill"),
    };
    const openMoreInfo = () => {
      this.dispatchEvent(
        new CustomEvent("hass-more-info", {
          detail: { entityId: this._config.entity },
          bubbles: true,
          composed: true,
        })
      );
    };
    const tile = this.querySelector(".tile");
    tile.addEventListener("click", openMoreInfo);
    tile.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        openMoreInfo();
      }
    });
    const iconEl = this.querySelector(".icon-container");
    iconEl.setAttribute("role", "button");
    iconEl.setAttribute("tabindex", "0");
    iconEl.style.cursor = "pointer";
    iconEl.title = _t(this._hass, "component.maintenance.card.mark_done_action");
    const markDone = (e) => {
      e.stopPropagation();
      _markDone(this, this._hass, this._config.entity, this._config.confirm ?? true);
    };
    iconEl.addEventListener("click", markDone);
    iconEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        e.stopPropagation();
        _markDone(this, this._hass, this._config.entity, this._config.confirm ?? true);
      }
    });
    this._built = true;
  }

  _renderError(message) {
    this.innerHTML = `<ha-card><div style="padding:12px;color:var(--error-color);">${message}</div></ha-card>`;
    this._built = false;
  }

}

const EDITOR_SCHEMA = [
  {
    name: "entity",
    required: true,
    selector: {
      entity: {
        filter: { integration: "maintenance", domain: "sensor" },
      },
    },
  },
  { name: "confirm", selector: { boolean: {} } },
];

class MaintenanceCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...(config || {}) };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      const form = document.createElement("ha-form");
      form.schema = EDITOR_SCHEMA;
      form.computeLabel = (s) =>
        _t(this._hass, `component.maintenance.card.editor.${s.name}`) || s.name;
      form.addEventListener("value-changed", (e) => {
        this._config = { ...this._config, ...e.detail.value };
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: this._config },
            bubbles: true,
            composed: true,
          })
        );
      });
      this._form = form;
      this.appendChild(form);
    }
    this._form.hass = this._hass;
    this._form.data = {
      entity: this._config.entity || "",
      confirm: this._config.confirm ?? true,
    };
  }
}

// -- List card -----------------------------------------------------------

const STATE_RANK = { overdue: 0, due_soon: 1, ok: 2 };

class MaintenanceListCard extends HTMLElement {
  static getStubConfig() {
    return { hide_ok: false, hide_when_empty: false, separate_items: false };
  }

  static async getConfigElement() {
    await customElements.whenDefined("maintenance-list-card-editor");
    return document.createElement("maintenance-list-card-editor");
  }

  setConfig(config) {
    this._config = {
      hide_ok: false,
      hide_when_empty: false,
      separate_items: false,
      ...(config || {}),
    };
    if (this._hass) this._update();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._config) this._update();
  }

  getCardSize() {
    if (this._isHiddenEmpty()) return 0;
    return Math.max(1, (this._rows || []).length);
  }

  _isHiddenEmpty() {
    return (
      !!this._config?.hide_when_empty &&
      Array.isArray(this._rows) &&
      this._rows.length === 0
    );
  }

  getLayoutOptions() {
    if (this._isHiddenEmpty()) {
      return { grid_columns: 0, grid_rows: 0, grid_min_columns: 0, grid_min_rows: 0 };
    }
    const rows = Math.max(1, (this._rows || []).length);
    return {
      grid_columns: 4,
      grid_rows: rows,
      grid_min_columns: 2,
      grid_min_rows: 1,
    };
  }

  connectedCallback() {
    if (this._config && this._hass) this._update();
  }

  disconnectedCallback() {
    if (this._tickHandle) {
      clearTimeout(this._tickHandle);
      this._tickHandle = null;
    }
  }

  _update() {
    const entities = this._config.entities
      ? this._config.entities.map((id) => this._hass.states[id]).filter(Boolean)
      : Object.values(this._hass.states).filter(
          (s) =>
            s.entity_id.startsWith("sensor.") &&
            s.attributes.criterion !== undefined &&
            s.attributes.progress !== undefined
        );

    let rows = entities.map((s) => this._toRow(s));
    this._totalCount = rows.length;
    if (this._config.hide_ok) rows = rows.filter((r) => r.status !== "ok");
    this._hiddenCount = this._totalCount - rows.length;
    rows.sort((a, b) => {
      const ra = STATE_RANK[a.status] ?? 3;
      const rb = STATE_RANK[b.status] ?? 3;
      if (ra !== rb) return ra - rb;
      return (b.progress ?? 0) - (a.progress ?? 0);
    });
    this._rows = rows;
    this._render();
  }

  _toRow(state) {
    const attrs = state.attributes;
    const status = state.state;
    return {
      entityId: state.entity_id,
      status,
      color: STATE_COLOR[status] || "var(--state-inactive-color)",
      icon: STATE_ICON[status] || "mdi:wrench-clock",
      name: attrs.friendly_name || state.entity_id,
      progress: Math.max(0, Math.min(100, Number(attrs.progress) || 0)),
      counter: Number(attrs.counter) || 0,
      threshold: Number(attrs.threshold) || 0,
      unit: attrs.counter_unit || "",
      dueIso: attrs.estimated_due_date || null,
    };
  }

  _render() {
    const rows = this._rows || [];

    // hide_when_empty: fully collapse the card in the section grid.
    if (rows.length === 0 && this._config.hide_when_empty) {
      this.style.display = "none";
      return;
    }
    this.style.display = "";

    this.classList.toggle("separate-items", !!this._config.separate_items);

    if (!this._built) this._build();

    if (rows.length === 0) {
      let msg;
      if (this._hiddenCount > 0) {
        const key =
          this._hiddenCount === 1
            ? "component.maintenance.card.empty_all_ok_one"
            : "component.maintenance.card.empty_all_ok_other";
        msg = _t(this._hass, key, { count: this._hiddenCount });
      } else {
        msg = _t(this._hass, "component.maintenance.card.empty_no_trackers");
      }
      this._els.list.innerHTML = `<div class="empty">${_escape(msg)}</div>`;
      this._scheduleTick();
      return;
    }

    const markDoneLabel = _escape(
      _t(this._hass, "component.maintenance.card.mark_done_action")
    );
    this._els.list.innerHTML = rows
      .map(
        (r, i) => `
        <div class="row" data-idx="${i}" role="button" tabindex="0"
             style="--state-color: ${r.color}">
          <div class="icon-container" role="button" tabindex="0"
               title="${markDoneLabel}">
            <div class="icon-bg"></div>
            <ha-icon icon="${r.icon}"></ha-icon>
          </div>
          <div class="info">
            <div class="line">
              <span class="name" title="${_escape(r.name)}">${_escape(r.name)}</span>
              <span class="due" data-idx="${i}"></span>
            </div>
            <div class="line bar-line">
              <div class="progress-bar"><div class="progress-fill" style="width:${r.progress}%"></div></div>
              <span class="counter">${_escape(_counterText(this._hass, r))}</span>
            </div>
          </div>
        </div>
      `
      )
      .join("");

    // Populate the relative "due" text using the same logic as the single card.
    this._els.list.querySelectorAll(".due").forEach((el) => {
      const idx = Number(el.dataset.idx);
      const r = rows[idx];
      el.textContent = _relativeDueText(this._hass, r.dueIso, r.status);
    });

    // Row click → open more-info. Icon click → mark done.
    const confirmOpt = this._config.confirm ?? true;
    this._els.list.querySelectorAll(".row").forEach((el) => {
      const idx = Number(el.dataset.idx);
      const entityId = rows[idx].entityId;
      const open = () =>
        this.dispatchEvent(
          new CustomEvent("hass-more-info", {
            detail: { entityId },
            bubbles: true,
            composed: true,
          })
        );
      el.addEventListener("click", open);
      el.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          open();
        }
      });
      const iconEl = el.querySelector(".icon-container");
      const markDone = (e) => {
        e.stopPropagation();
        _markDone(this, this._hass, entityId, confirmOpt);
      };
      iconEl.addEventListener("click", markDone);
      iconEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          e.stopPropagation();
          _markDone(this, this._hass, entityId, confirmOpt);
        }
      });
    });

    this._scheduleTick();
  }

  _build() {
    this.innerHTML = `
      <ha-card>
        <div class="list"></div>
        <style>
          :host { display: block; }
          ha-card {
            padding: 0;
            /* HA's default 1px border on ha-card shrinks the client area by
               2px, so N rows @ 56px each overflow by 2px. Both symptoms
               (focus outline clipped at bottom, and 2px scroll shift when
               tabbing to the last row) trace back to that. Zero the border
               so client area == offset height. */
            border: 0;
            height: 100%;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            overflow: clip;
          }
          .list {
            display: flex;
            flex-direction: column;
            min-height: 0;
            gap: var(--row-gap, 8px);
          }
          .empty {
            padding: 16px;
            min-height: 56px;
            box-sizing: border-box;
            display: flex;
            align-items: center;
            color: var(--secondary-text-color);
            font-size: 0.9em;
          }
          .row {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 8px 16px;
            cursor: pointer;
            min-width: 0;
            box-sizing: border-box;
            min-height: var(--row-height, 56px);
            position: relative;
          }
          /* First/last rows inherit the card's corner radius so their focus
             ring and hover bg follow the card silhouette. */
          .row:first-child {
            border-top-left-radius: var(--ha-card-border-radius, 12px);
            border-top-right-radius: var(--ha-card-border-radius, 12px);
          }
          .row:last-child {
            border-bottom-left-radius: var(--ha-card-border-radius, 12px);
            border-bottom-right-radius: var(--ha-card-border-radius, 12px);
          }
          .row:focus { outline: none; }
          .row::before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            border-radius: inherit;
            border: 2px solid transparent;
            box-sizing: border-box;
          }
          .row:focus-visible::before {
            border-color: var(--state-color);
          }
          .icon-container {
            position: relative;
            width: 34px;
            height: 34px;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            border-radius: 50%;
          }
          .icon-container:hover .icon-bg { opacity: 0.35; }
          .icon-container:focus { outline: none; }
          .icon-container:focus-visible {
            outline: none;
            /* box-shadow follows border-radius (circle) reliably; outline can fall back to a rectangle on some browsers. */
            box-shadow: 0 0 0 2px var(--state-color);
          }
          .icon-bg {
            position: absolute;
            inset: 0;
            border-radius: 50%;
            background: var(--state-color);
            opacity: 0.2;
          }
          ha-icon {
            position: relative;
            color: var(--state-color);
            --mdc-icon-size: 22px;
          }
          .info {
            flex: 1;
            min-width: 0;
            display: flex;
            flex-direction: column;
            gap: 2px;
          }
          .line {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            min-width: 0;
          }
          .name {
            font-weight: 500;
            color: var(--primary-text-color);
            font-size: 0.95em;
            line-height: 1.2;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
          .due, .counter {
            color: var(--secondary-text-color);
            font-size: 0.78em;
            line-height: 1.2;
            white-space: nowrap;
            flex-shrink: 0;
          }
          .progress-bar {
            flex: 1;
            height: 4px;
            background: var(--divider-color);
            border-radius: 2px;
            overflow: hidden;
            min-width: 30px;
          }
          .progress-fill {
            height: 100%;
            border-radius: 2px;
            background: var(--state-color);
            transition: width 0.3s ease, background 0.3s ease;
          }
          /* separate_items: each row renders as an individual tile card. */
          maintenance-list-card.separate-items > ha-card {
            background: transparent;
            box-shadow: none;
          }
          maintenance-list-card.separate-items .row {
            background: var(--ha-card-background, var(--card-background-color, #fff));
            box-shadow: var(--ha-card-box-shadow, none);
            border-radius: var(--ha-card-border-radius, 12px);
          }
        </style>
      </ha-card>
    `;
    this._els = {
      list: this.querySelector(".list"),
    };
    this._built = true;
  }

  _scheduleTick() {
    if (this._tickHandle) {
      clearTimeout(this._tickHandle);
      this._tickHandle = null;
    }
    if (!this.isConnected) return;
    const rows = this._rows || [];
    const diffs = rows
      .map((r) => (r.dueIso ? Math.abs(new Date(r.dueIso).getTime() - Date.now()) / 1000 : Infinity))
      .filter((d) => Number.isFinite(d));
    if (diffs.length === 0) return;
    const minDiff = Math.min(...diffs);
    let ms;
    if (minDiff < 60) ms = 1000;
    else if (minDiff < 3600) ms = 30_000;
    else if (minDiff < 86400) ms = 300_000;
    else ms = 3_600_000;
    this._tickHandle = setTimeout(() => this._tick(), ms);
  }

  _tick() {
    if (!this.isConnected || !this._built) return;
    const rows = this._rows || [];
    this._els.list.querySelectorAll(".due").forEach((el) => {
      const idx = Number(el.dataset.idx);
      const r = rows[idx];
      if (r) el.textContent = _relativeDueText(this._hass, r.dueIso, r.status);
    });
    this._scheduleTick();
  }
}

const LIST_EDITOR_SCHEMA = [
  { name: "hide_ok", selector: { boolean: {} } },
  { name: "hide_when_empty", selector: { boolean: {} } },
  { name: "separate_items", selector: { boolean: {} } },
  { name: "confirm", selector: { boolean: {} } },
];

class MaintenanceListCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...(config || {}) };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      const form = document.createElement("ha-form");
      form.schema = LIST_EDITOR_SCHEMA;
      form.computeLabel = (s) =>
        _t(this._hass, `component.maintenance.card.editor.${s.name}`) || s.name;
      form.addEventListener("value-changed", (e) => {
        this._config = { ...this._config, ...e.detail.value };
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: this._config },
            bubbles: true,
            composed: true,
          })
        );
      });
      this._form = form;
      this.appendChild(form);
    }
    this._form.hass = this._hass;
    this._form.data = {
      hide_ok: this._config.hide_ok ?? false,
      hide_when_empty: this._config.hide_when_empty ?? false,
      separate_items: this._config.separate_items ?? false,
      confirm: this._config.confirm ?? true,
    };
  }
}

// -- Shared helpers used by both cards -----------------------------------

function _escape(s) {
  return String(s).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function _counterText(hass, r) {
  return _fmtProgress(hass, r.counter, r.threshold, r.unit);
}

function _confirmDialog(_dispatchEl, text, title, okLabel, cancelLabel) {
  return new Promise((resolve) => {
    let settled = false;
    const settle = (v) => {
      if (settled) return;
      settled = true;
      try {
        // The modern ha-dialog has no close(); it is driven by `open`.
        if (typeof dialog.close === "function") dialog.close();
        else dialog.open = false;
      } catch (_) {}
      setTimeout(() => dialog.remove(), 200);
      resolve(v);
    };

    const dialog = document.createElement("ha-dialog");
    // HA replaced the mwc-based ha-dialog: the title is `headerTitle` and the
    // actions live in a single `footer` slot. The old `primaryAction` /
    // `secondaryAction` slots no longer exist, so buttons assigned to them are
    // never slotted and render at zero size. Detect which generation we are on.
    const modernDialog = "headerTitle" in dialog;
    if (modernDialog) dialog.headerTitle = title || "Confirm";
    else dialog.heading = title || "Confirm";
    dialog.open = true;

    const body = document.createElement("div");
    body.textContent = text;
    body.style.padding = "8px 0";
    dialog.appendChild(body);

    // The modern dialog exposes one `footer` slot, so the actions need their own
    // row to sit side by side; the mwc-era dialog slotted them individually.
    let actions = dialog;
    if (modernDialog) {
      actions = document.createElement("div");
      actions.setAttribute("slot", "footer");
      actions.style.display = "flex";
      actions.style.justifyContent = "flex-end";
      actions.style.gap = "8px";
      actions.style.width = "100%";
      dialog.appendChild(actions);
    }

    const cancel = document.createElement("ha-button");
    if (!modernDialog) cancel.setAttribute("slot", "secondaryAction");
    cancel.setAttribute("appearance", "plain");
    cancel.textContent = cancelLabel || "Cancel";
    cancel.addEventListener("click", () => settle(false));
    actions.appendChild(cancel);

    const ok = document.createElement("ha-button");
    if (!modernDialog) ok.setAttribute("slot", "primaryAction");
    ok.setAttribute("dialogInitialFocus", "");
    ok.textContent = okLabel || "OK";
    ok.addEventListener("click", () => settle(true));
    actions.appendChild(ok);

    // mwc-dialog doesn't wire Enter → default action; handle it ourselves.
    dialog.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && !ev.shiftKey && !ev.ctrlKey && !ev.metaKey) {
        ev.preventDefault();
        settle(true);
      }
    });

    dialog.addEventListener("closed", (ev) => {
      settle(ev.detail?.action === "ok");
    });
    document.body.appendChild(dialog);
  });
}

async function _markDone(dispatchEl, hass, entityId, confirmOpt) {
  if (confirmOpt) {
    const name = hass.states[entityId]?.attributes?.friendly_name || entityId;
    const msg =
      typeof confirmOpt === "string"
        ? confirmOpt
        : _t(hass, "component.maintenance.card.confirm_body", { name });
    const ok = await _confirmDialog(
      dispatchEl,
      msg,
      _t(hass, "component.maintenance.card.confirm_title"),
      _t(hass, "component.maintenance.card.confirm_ok"),
      _t(hass, "component.maintenance.card.confirm_cancel")
    );
    if (!ok) return;
  }
  try {
    await hass.callService(
      "maintenance",
      "mark_done",
      {},
      { entity_id: entityId }
    );
  } catch (e) {
    console.error("[maintenance-card] mark_done failed:", e);
  }
}

// Register the elements.
//
// HA's frontend replaces `window.customElements` with a scoped-registry
// polyfill while it boots. This module is injected via `add_extra_js_url`, so
// module execution order against that swap is a race: if we run first we define
// into the *native* registry, the polyfill then shadows it, and HA reports
// "Custom element doesn't exist: maintenance-list-card" for the whole session.
// Defining again into the swapped-in registry is legal (it is a different
// registry object), so keep re-asserting the registration for a short window
// after load. HA's own `whenDefined` hook then rebuilds any error cards.
const CARD_REGISTRATIONS = [
  ["maintenance-card", MaintenanceCard],
  ["maintenance-card-editor", MaintenanceCardEditor],
  ["maintenance-list-card", MaintenanceListCard],
  ["maintenance-list-card-editor", MaintenanceListCardEditor],
];

function registerCards() {
  const registry = window.customElements;
  if (!registry) return;
  for (const [name, cls] of CARD_REGISTRATIONS) {
    if (registry.get(name)) continue;
    try {
      registry.define(name, cls);
    } catch (e) {
      console.error("[maintenance-card] failed to define", name, cls);
    }
  }
}

registerCards();

// Re-assert across the polyfill swap. Cheap, and stops once HA has booted.
let registerTicks = 0;
const registerTimer = setInterval(() => {
  registerCards();
  if (++registerTicks >= 60) clearInterval(registerTimer);
}, 200);
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", registerCards);
}
window.addEventListener("load", registerCards);

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "maintenance-card")) {
  window.customCards.push({
    type: "maintenance-card",
    name: "Maintenance Tracker",
    description: "Tile showing a maintenance tracker's status and progress.",
    preview: true,
  });
}
if (!window.customCards.some((c) => c.type === "maintenance-list-card")) {
  window.customCards.push({
    type: "maintenance-list-card",
    name: "Maintenance List",
    description: "Lists all maintenance trackers, sorted by urgency.",
    preview: true,
  });
}

console.info(
  `%c MAINTENANCE-CARD %c v${CARD_VERSION} `,
  "color:white;background:#4caf50;padding:2px 6px;border-radius:3px 0 0 3px;font-weight:600",
  "color:#4caf50;background:#eee;padding:2px 6px;border-radius:0 3px 3px 0;font-weight:600"
);
