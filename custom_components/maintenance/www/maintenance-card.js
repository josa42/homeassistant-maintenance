const CARD_VERSION = "0.1.4";

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
          ha-card { padding: 12px; cursor: pointer; box-sizing: border-box; }
          .tile { display: flex; align-items: center; gap: 12px; min-width: 0; }
          .icon-container {
            position: relative; width: 40px; height: 40px; flex-shrink: 0;
            display: flex; align-items: center; justify-content: center;
          }
          .icon-bg {
            position: absolute; inset: 0; border-radius: 50%;
            background: var(--state-color); opacity: 0.2;
          }
          ha-icon {
            position: relative; color: var(--state-color); --mdc-icon-size: 24px;
          }
          .info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
          .row {
            display: flex; align-items: center; justify-content: space-between;
            gap: 8px; min-width: 0;
          }
          .name {
            font-weight: 500; color: var(--primary-text-color);
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
          }
          .due, .counter {
            color: var(--secondary-text-color); font-size: 0.85em;
            white-space: nowrap; flex-shrink: 0;
          }
          .progress-bar {
            flex: 1; height: 6px; background: var(--divider-color);
            border-radius: 3px; overflow: hidden; min-width: 30px;
          }
          .progress-fill {
            height: 100%; border-radius: 3px; background: var(--state-color);
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

console.info(
  `%c MAINTENANCE-CARD %c v${CARD_VERSION} `,
  "color:white;background:#4caf50;padding:2px 6px;border-radius:3px 0 0 3px;font-weight:600",
  "color:#4caf50;background:#eee;padding:2px 6px;border-radius:0 3px 3px 0;font-weight:600"
);
