const CARD_VERSION = "0.2.1";

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
    this._els.due.textContent = this._relativeDue(attrs.estimated_due_date, status);
    this._els.counter.textContent = threshold
      ? `${this._fmt(counter)} / ${this._fmt(threshold)} ${unit}`.trim()
      : `${this._fmt(counter)} ${unit}`.trim();
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
    this._els.due.textContent = this._relativeDue(
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
            padding: 6px 12px;
            cursor: pointer;
            box-sizing: border-box;
            height: 100%;
            display: flex;
            align-items: center;
          }
          .tile { display: flex; align-items: center; gap: 10px; min-width: 0; width: 100%; }
          .icon-container {
            position: relative; width: 34px; height: 34px; flex-shrink: 0;
            display: flex; align-items: center; justify-content: center;
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
          .tile:focus-visible {
            outline: 2px solid var(--state-color); outline-offset: 2px; border-radius: 6px;
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
    this._built = true;
  }

  _renderError(message) {
    this.innerHTML = `<ha-card><div style="padding:12px;color:var(--error-color);">${message}</div></ha-card>`;
    this._built = false;
  }

  _fmt(n) {
    if (!Number.isFinite(n)) return "";
    return Number.isInteger(n) ? String(n) : n.toFixed(1);
  }

  _relativeDue(dueIso, status) {
    if (!dueIso) return this._stateLabel(status);
    const due = new Date(dueIso);
    if (isNaN(due.getTime())) return this._stateLabel(status);
    const diffSec = (due.getTime() - Date.now()) / 1000;
    if (diffSec <= 0 && status !== "overdue") return this._stateLabel(status);
    if (diffSec > 0 && status === "overdue") return this._stateLabel(status);

    const abs = Math.abs(diffSec);
    let value, unit;
    if (abs < 60) { value = diffSec; unit = "second"; }
    else if (abs < 3600) { value = diffSec / 60; unit = "minute"; }
    else if (abs < 86400) { value = diffSec / 3600; unit = "hour"; }
    else if (abs < 2592000) { value = diffSec / 86400; unit = "day"; }
    else if (abs < 31536000) { value = diffSec / 2592000; unit = "month"; }
    else { value = diffSec / 31557600; unit = "year"; }
    const lang = (this._hass && this._hass.language) || "en";
    const rtf = new Intl.RelativeTimeFormat(lang, { numeric: "auto" });
    return rtf.format(Math.round(value), unit);
  }

  _stateLabel(status) {
    if (this._hass && this._hass.localize) {
      const key = `component.maintenance.entity.sensor.tracker.state.${status}`;
      const label = this._hass.localize(key);
      if (label) return label;
    }
    return (
      { ok: "OK", due_soon: "Due soon", overdue: "Overdue" }[status] || ""
    );
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
        s.name === "entity" ? "Maintenance tracker" : s.name;
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
    this._form.data = { entity: this._config.entity || "" };
  }
}

// -- List card -----------------------------------------------------------

const STATE_RANK = { overdue: 0, due_soon: 1, ok: 2 };

class MaintenanceListCard extends HTMLElement {
  static getStubConfig() {
    return { title: "Maintenance", hide_ok: false };
  }

  static async getConfigElement() {
    await customElements.whenDefined("maintenance-list-card-editor");
    return document.createElement("maintenance-list-card-editor");
  }

  setConfig(config) {
    this._config = { title: "Maintenance", hide_ok: false, ...(config || {}) };
    if (this._hass) this._update();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._config) this._update();
  }

  getCardSize() {
    return Math.max(1, (this._rows || []).length);
  }

  getLayoutOptions() {
    const rows = Math.max(1, (this._rows || []).length);
    return {
      grid_columns: 4,
      grid_rows: rows + (this._config?.title !== "" ? 1 : 0),
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
    if (this._config.hide_ok) rows = rows.filter((r) => r.status !== "ok");
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
    if (!this._built) this._build();

    const rows = this._rows || [];
    this._els.title.textContent = this._config.title || "";
    this._els.title.style.display = this._config.title ? "" : "none";

    if (rows.length === 0) {
      this._els.list.innerHTML = `<div class="empty">No maintenance trackers configured.</div>`;
      this._scheduleTick();
      return;
    }

    this._els.list.innerHTML = rows
      .map(
        (r, i) => `
        <div class="row" data-idx="${i}" role="button" tabindex="0"
             style="--state-color: ${r.color}">
          <div class="icon-container">
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
              <span class="counter">${_counterText(r)}</span>
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
      el.textContent = _relativeDue(r.dueIso, r.status, this._hass);
    });

    // Row click → open more-info.
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
    });

    this._scheduleTick();
  }

  _build() {
    this.innerHTML = `
      <ha-card>
        <div class="header"></div>
        <div class="list"></div>
        <style>
          :host { display: block; }
          ha-card { padding: 8px 0; }
          .header {
            padding: 4px 16px 8px;
            font-weight: 500;
            font-size: 1.05em;
            color: var(--primary-text-color);
          }
          .empty {
            padding: 12px 16px;
            color: var(--secondary-text-color);
          }
          .row {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 8px 16px;
            cursor: pointer;
            min-width: 0;
          }
          .row:hover { background: var(--divider-color); }
          .row:focus { outline: none; }
          .row:focus-visible {
            outline: 2px solid var(--state-color);
            outline-offset: -2px;
          }
          .icon-container {
            position: relative;
            width: 34px;
            height: 34px;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
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
            gap: 4px;
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
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
          .due, .counter {
            color: var(--secondary-text-color);
            font-size: 0.85em;
            white-space: nowrap;
            flex-shrink: 0;
          }
          .progress-bar {
            flex: 1;
            height: 6px;
            background: var(--divider-color);
            border-radius: 3px;
            overflow: hidden;
            min-width: 30px;
          }
          .progress-fill {
            height: 100%;
            border-radius: 3px;
            background: var(--state-color);
            transition: width 0.3s ease, background 0.3s ease;
          }
        </style>
      </ha-card>
    `;
    this._els = {
      title: this.querySelector(".header"),
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
      if (r) el.textContent = _relativeDue(r.dueIso, r.status, this._hass);
    });
    this._scheduleTick();
  }
}

const LIST_EDITOR_SCHEMA = [
  { name: "title", selector: { text: {} } },
  { name: "hide_ok", selector: { boolean: {} } },
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
        ({ title: "Title", hide_ok: "Hide OK trackers" }[s.name] || s.name);
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
      title: this._config.title ?? "Maintenance",
      hide_ok: this._config.hide_ok ?? false,
    };
  }
}

// -- Shared helpers used by both cards -----------------------------------

function _escape(s) {
  return String(s).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function _counterText(r) {
  const fmt = (n) => (Number.isInteger(n) ? String(n) : n.toFixed(1));
  if (!Number.isFinite(r.counter)) return "";
  return r.threshold
    ? `${fmt(r.counter)} / ${fmt(r.threshold)} ${r.unit}`.trim()
    : `${fmt(r.counter)} ${r.unit}`.trim();
}

function _relativeDue(dueIso, status, hass) {
  const label = (s) => {
    if (hass && hass.localize) {
      const key = `component.maintenance.entity.sensor.tracker.state.${s}`;
      const t = hass.localize(key);
      if (t) return t;
    }
    return { ok: "OK", due_soon: "Due soon", overdue: "Overdue" }[s] || "";
  };
  if (!dueIso) return label(status);
  const due = new Date(dueIso);
  if (isNaN(due.getTime())) return label(status);
  const diffSec = (due.getTime() - Date.now()) / 1000;
  if (diffSec <= 0 && status !== "overdue") return label(status);
  if (diffSec > 0 && status === "overdue") return label(status);
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

// Register early — before any classes are used elsewhere — to survive races
// where HA's dashboard renderer looks up the element before the module has
// finished executing.
try {
  if (!customElements.get("maintenance-card")) {
    customElements.define("maintenance-card", MaintenanceCard);
  }
  if (!customElements.get("maintenance-card-editor")) {
    customElements.define("maintenance-card-editor", MaintenanceCardEditor);
  }
  if (!customElements.get("maintenance-list-card")) {
    customElements.define("maintenance-list-card", MaintenanceListCard);
  }
  if (!customElements.get("maintenance-list-card-editor")) {
    customElements.define("maintenance-list-card-editor", MaintenanceListCardEditor);
  }
} catch (e) {
  console.error("[maintenance-card] failed to define custom element:", e);
}

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
