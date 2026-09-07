# AGENTS.md

Notes for AI coding agents working on this repo. Written from lessons that only
became obvious after they bit. Read before proposing a "fix", especially for
UI, HA-integration, or i18n changes.

## Repo shape

- Custom Home Assistant integration in `custom_components/maintenance/`.
- Ships its own Lovelace card at `custom_components/maintenance/www/maintenance-card.js`,
  auto-registered via `add_extra_js_url`. Bumping `CARD_VERSION` in both
  `__init__.py` and the JS is required — the query string is the cache-buster.
- Pattern: **one config entry per tracker** (idiomatic HA "helper"). Do not
  reintroduce single-instance parent + subentries; the Helpers UI can't drive
  that path (see below).
- Tests use `pytest-homeassistant-custom-component` and live in `tests/`.
  Set up with `make install` (creates `./venv`), then `make test`. Lint with
  `make lint` (ruff, configured in `ruff.toml`).
- Real-HA validation stack: `make dev-up` (see `docker-compose.yml`) plus
  Puppeteer at `/tmp/node_modules/puppeteer-core` for scripted UI checks.
  `make dev-restart` reloads after code changes, `make dev-logs` follows logs.

## Validate against real HA, not just simulations

Several attempted CSS/JS "fixes" passed in bare-HTML probes and headless
Chrome but broke inside the actual HA dashboard because HA's shadow-DOM
wrapping (`hui-card`, `hui-sections-view`, `ha-card`) has properties that
bare pages don't have.

Rules of thumb:

- If the bug is about layout, focus, scroll, or paint, **reproduce in the
  actual dashboard** at `http://localhost:8123/dashboard-maintenance/0`
  before shipping. Login is `test` / `test`.
- Puppeteer against the real HA is fine and works — walk into shadow DOMs via
  `[...node.children, ...(node.shadowRoot ? [node.shadowRoot] : [])]`.
- Measure what actually moved: `element.getBoundingClientRect().top` for each
  suspect node, not just the visible symptom.

## HA-specific gotchas that cost time

### `overflow: hidden` on `ha-card` is a scroll container

`ha-card` has a default `border: 1px solid` (visible or transparent). That
makes `clientHeight = offsetHeight − 2px`. If your content fills
`offsetHeight`, it overflows the client area by 2 px. `overflow: hidden`
doesn't help — the element is still programmatically scrollable, and the
browser calls `scrollIntoView` on the last focused child, scrolling
`ha-card.scrollTop` from 0 → 2. The whole card visually shifts by 2 px.

Fix: `overflow: clip` (does not establish a scroll container) **and** `border: 0`
to eliminate the 2 px difference at the source. Both were needed in
`maintenance-list-card`.

### Row focus outline clipped at first/last row

Rows abut the `ha-card` corners; a plain `outline: 2px` at the row edge is
clipped by the card's `border-radius` + `overflow` clip. Fix that worked:

- Give first row `border-top-{left,right}-radius: var(--ha-card-border-radius)`
  and mirror on last row.
- Use a `::before` pseudo-element with `border-radius: inherit` and a
  transparent border that goes coloured on `:focus-visible`. Renders inside
  the row's border-box, so clipping is impossible.

### Whole-card focus outline for a tile

`ha-card:has(.tile:focus-visible)` is the modern selector to move focus from
an inner element up to the ha-card silhouette, matching HA's own tile card.
Firefox 121+ / Chrome 105+.

### HA's `ha-button` variants + appearances

HA's ha-button (Web Awesome under the hood) accepts:

- `variant`: `default`, `brand`, `neutral`, `danger`, `warning`, `success`, `solid`
- `appearance`: `filled`, `accent`, `plain`, `outlined`

HA's own dialogs use `<ha-button appearance="plain" slot="secondaryAction">`
for cancel/dismiss and a plain `<ha-button slot="primaryAction">` for the
primary action. Match that instead of inventing a style.

### mwc-dialog / ha-dialog Enter key

`mwc-dialog` does **not** wire Enter to `defaultAction` automatically. Add an
explicit `keydown` listener on the dialog and confirm on `Enter`. Setting
`dialogInitialFocus` on the primary button also helps.

### Frontend `dialog-box` lazy-loading

HA's confirmation `dialog-box` is code-split. You cannot import it from a
custom card — the bundled chunk URL is version-hashed. Build your own
dialog with `<ha-dialog>` + `<ha-button>`, which are always registered.

### `add_extra_js_url` caching + service worker

The URL is served with cache headers off, but HA's service worker still
caches. Users must:

1. DevTools → Application → Service Workers → **Unregister** (or use private
   window)
2. Bump `CARD_VERSION` (query string) so any middle cache also misses

## i18n and formatting

- Everything user-facing goes through `hass.localize(...)` against
  `component.maintenance.*`. Both `en` and `de` translation files must stay
  in sync — `strings.json` is copied to `translations/en.json` on each edit.
- Card JS has an `EN_FALLBACK` map for the rare case `hass.localize` returns
  falsy before HA finishes booting.
- Never build user-visible strings with template literals; use `_t(hass, key, params)`
  which supports `{name}`-style interpolation.
- Numbers: `Intl.NumberFormat(hass.language, ...)`. Never `n.toFixed()`.
- Durations: `Intl.NumberFormat({ style: 'unit', unit: 'day', unitDisplay: 'long' })`
  for whole values ("3 days" / "3 Tage"), `unitDisplay: 'narrow'` for compact
  ("3d" / "3 T"), digital `H:MM` / `M:SS` for fractional minute/hour counters.
  Never emit decimals for time.
- Whole-value counter + threshold with the same unit render as
  `N / M unit` (unit only once). Pluralisation follows the threshold via Intl
  for standard units; custom units (e.g. `uses`) provide `_one` / `_other`
  translation keys.

## Config-flow patterns

- Every criterion has its own `_CRITERION_SCHEMAS` entry keyed by the
  criterion constant.
- Selectors that need localized labels use `SelectSelector` with
  `translation_key="..."` — HA's frontend then reads
  `selector.<translation_key>.options.<value>` from strings.json.
- `vol.In([...])` gives raw keys with no localization. Always use
  `SelectSelector` for user-facing choices.
- One-shot seed pattern: put `last_done` (or similar init-only value) into
  `entry.data`, apply it in `async_setup_entry`, then strip it via
  `hass.config_entries.async_update_entry(entry, data=new_data)`. The value
  survives one boot and never clobbers runtime updates.

## Never / always

- **Never** guess a HA CSS variable — grep the HA frontend bundle
  (`hass_frontend/frontend_latest/*.js` inside the container).
- **Never** rely on browser cache/hard-refresh being enough for card debugging;
  bump `CARD_VERSION` **and** clear the service worker for definitive tests.
- **Never** ship a JS-side "fix" without reproducing on the real HA dashboard;
  the shadow-DOM chain is what changes behaviour.
- **Never** batch unrelated changes into one commit. User rule: commit
  individually.
- **Always** run `make test` after any Python change, and `make lint` before
  committing.
- **Always** update `translations/en.json` after editing `strings.json` (they
  are literally the same file — cp one to the other).
- **Always** update `translations/de.json` when adding user-facing strings.

## When touching the list card

- `_fmtProgress(hass, counter, threshold, unit)` is the single source of
  truth for the counter/threshold display. If you touch counter rendering,
  edit this one place — the single card and list card both use it.
- `getLayoutOptions()` on the list card returns `grid_rows: N`. HA reserves
  `N × row-height + (N−1) × row-gap`. Match the card's height to that with
  `.list { gap: var(--row-gap, 8px); }` and `.row { min-height: var(--row-height, 56px); }`.
  Don't add outer padding on `ha-card` — that breaks the grid math.
- `separate_items: true` mode adds `--ha-card-background` and border-radius
  to each row and drops the outer card's background. Test both modes when
  changing row visuals.

## Release

`scripts/release.sh <version>` — bumps `manifest.json`, `CARD_VERSION` in
`__init__.py` and `maintenance-card.js`, runs tests, commits, tags, pushes.
