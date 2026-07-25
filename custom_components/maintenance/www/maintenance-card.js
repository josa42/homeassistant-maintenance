const CARD_VERSION = "0.3.23";

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
    iconEl.title = "Mark done";
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
        ({ entity: "Maintenance tracker", confirm: "Confirm before mark done" }[
          s.name
        ] || s.name);
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
        msg = this._hiddenCount === 1
          ? "Nothing due — 1 tracker is up to date."
          : `Nothing due — all ${this._hiddenCount} trackers are up to date.`;
      } else {
        msg = "No maintenance trackers configured.";
      }
      this._els.list.innerHTML = `<div class="empty">${msg}</div>`;
      this._scheduleTick();
      return;
    }

    this._els.list.innerHTML = rows
      .map(
        (r, i) => `
        <div class="row" data-idx="${i}" role="button" tabindex="0"
             style="--state-color: ${r.color}">
          <div class="icon-container" role="button" tabindex="0"
               title="Mark done">
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
      if (r) el.textContent = _relativeDue(r.dueIso, r.status, this._hass);
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
        ({
          hide_ok: "Hide OK trackers",
          hide_when_empty: "Hide card when empty",
          separate_items: "Render each item as its own card",
          confirm: "Confirm before mark done",
        }[s.name] || s.name);
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

function _counterText(r) {
  const fmt = (n) => (Number.isInteger(n) ? String(n) : n.toFixed(1));
  if (!Number.isFinite(r.counter)) return "";
  return r.threshold
    ? `${fmt(r.counter)} / ${fmt(r.threshold)} ${r.unit}`.trim()
    : `${fmt(r.counter)} ${r.unit}`.trim();
}

function _confirmDialog(_dispatchEl, text, title) {
  return new Promise((resolve) => {
    let settled = false;
    const settle = (v) => {
      if (settled) return;
      settled = true;
      try {
        dialog.close?.();
      } catch (_) {}
      setTimeout(() => dialog.remove(), 200);
      resolve(v);
    };

    const dialog = document.createElement("ha-dialog");
    dialog.heading = title || "Confirm";
    dialog.open = true;
    // mwc-dialog: pressing Enter triggers the button whose dialogAction matches
    // defaultAction. Assigning "ok" here makes Enter confirm.
    dialog.defaultAction = "ok";

    const body = document.createElement("div");
    body.textContent = text;
    body.style.padding = "8px 0";
    dialog.appendChild(body);

    const cancel = document.createElement("ha-button");
    cancel.setAttribute("slot", "secondaryAction");
    cancel.setAttribute("dialogAction", "cancel");
    cancel.setAttribute("appearance", "plain");
    cancel.textContent = "Cancel";
    cancel.addEventListener("click", () => settle(false));
    dialog.appendChild(cancel);

    const ok = document.createElement("ha-button");
    ok.setAttribute("slot", "primaryAction");
    ok.setAttribute("dialogAction", "ok");
    ok.setAttribute("dialogInitialFocus", "");
    ok.textContent = "Mark done";
    ok.addEventListener("click", () => settle(true));
    dialog.appendChild(ok);

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
        : `Mark "${name}" as done?`;
    const ok = await _confirmDialog(dispatchEl, msg, "Maintenance");
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
