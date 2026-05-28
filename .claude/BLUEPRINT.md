# BLUEPRINT.md — Implementation Plan: Argentina Weekly Macro Monitor

> **What this file is.** A build-ready engineering plan to evolve the existing pipeline into the hedge-fund weekly monitor specified in `REPORT_BLUEPRINT.md`. It is written to be handed to an implementing model (Sonnet/Haiku). Every task names the exact file, function signature, data source, and acceptance test. Read `REPORT_BLUEPRINT.md` for the *analytical* spec (what each section means); read this for *how to build it*.
>
> **Companion docs:** `CLAUDE.md` (architecture + conventions — authoritative), `DATA_SOURCES.md` (series IDs), `CODING_CHECKLIST.md` (do/don't rules). Follow those; this plan does not repeat them.

---

## 0. Context & Goal

The current pipeline answers "is Argentina building sustainable real wage growth?" and renders 5 PDFs. The target product is a **weekly trading monitor** whose spine is **external solvency** — *does the BCRA have, or can it acquire, enough dollars to defend the regime?* The report reorients around reserves, FX regime, and the financing wall, with the real economy demoted to "political runway" context.

**This is a phased evolution, not a rewrite.** The ingestion → signals → sections → report architecture stays. We add new series, new signal metrics, and new section renderers, reusing existing clients and PDF helpers.

**Guiding priority order:** dollars first (reserves, FX, flows, debt), anchors second (inflation, fiscal, peso curve), real economy last. Build the spine before anything else.

---

## 1. Target vs. Current State — the gap map

| REPORT_BLUEPRINT section | Current state | Build effort |
|---|---|---|
| §2 Reserves — waterfall (Gross→NIR→Net-Net) | **`net_reserves_usd_bn` is referenced but NEVER computed** (see §3 below) | **HIGH — keystone** |
| §2 Reserve-change decomposition | Not built | HIGH |
| §2 IMF NIR target tracking | Not built (no target data) | MED (needs manual config) |
| §3 FX regime (parallels, brecha, REER) | Only official FX exists | MED–HIGH (new sources) |
| §4 External flows & dollar calendar | Trade + CA exist; no forward calendar | MED |
| §5 Inflation | Built (`signals/inflation.py`, SVAR) — needs "last-mile vs crawl" metric | LOW |
| §6 Fiscal + quasi-fiscal | Built (`signals/fiscal.py`) — needs revenue-quality + LEFI | MED |
| §7 Debt & financing wall | Debt stock built; no forward payment calendar/coverage ratio | MED |
| §8 Peso curve & monetary | Not built (M2 exists) | MED–HIGH (new sources) |
| §9–§12 Real economy | Largely built (gdp, production, labor, consumption signals) | LOW (reframe only) |
| §13 Political risk | Not built (qualitative) | LOW (manual config) |
| §14 Asset dashboard | Not built | MED |
| §1 Weekly scorecard + verdict ladder + diff | Master scorecard exists; no weekly diff, no regime-ladder verdict | MED |

---

## 2. Architecture you must build within — REUSE these, do not reinvent

**Layer 1 clients** (`ingestion/client.py`):
- `DatosClient().fetch(ids: list[str], limit, start_date=None, frequency=None) -> DataFrame|None` — datos.gob.ar time series. Columns = `["date", <series_id>...]`.
- `WorldBankClient().fetch(indicator, mrv) -> DataFrame|None`.
- `PdfClient()` — `.fetch_bytes`, `.extract_text`, `.extract_tables`, `.find`, `.fetch_text`. Caches PDFs as hex.
- Helpers: `_start(months, buffer=14)`, `to_monthly_last(raw, value_col)`.

**`utils`** exposes: `fetch_json`, `get_logger`, `load_cache`, `save_cache`, `CACHE_DIR`, and the dir constants `RESERVES_DIR`, `EXTERNAL_DIR`, `SIGNALS_DIR`, `CHARTS_DIR`, `REPORTS_DIR`, plus `compute_real_values`. **Add any new data dir constant to `utils`, do not hardcode paths.**

**Layer 2 orchestration** (`ingestion/fetch_all.py::fetch_all() -> (data: dict, warnings: list[str])`): every new fetch function gets called here, its result added to the `data` dict, failures appended to `warnings` (never raise — degrade gracefully).

**Layer 3 signal contract** — every `signals/<domain>.py` exposes `compute() -> dict`, reads CSVs, writes `data/signals/signals_<domain>.json` with this exact schema:
```
{ "domain", "as_of_date", "data_quality": "good|partial|poor",
  "metrics": {...}, "flags": ["CRITICAL:|WARNING:|NOTE:|POSITIVE: ..."],
  "trend": "improving|deteriorating|stable|mixed",
  "connection_to_master_variable": "positive|negative|neutral",
  "summary": "one sentence" }
```
Register new signal `compute()` calls in `main.py::run_pipeline` (the block around lines 56–65).

**Layer 5 PDF toolkit** — subclass `ArgentinaPDF` from `report/build.py`. Reuse the helper pattern in `sections/reserves/report.py::ReservesPDF`: `kpi_row(items)`, `subsection(text)`, `note(text)`, `formula_block(lines)`, `body_text(text)`. **All strings go through `_safe()`** (fpdf2 is Latin-1). **`matplotlib.use("Agg")` before any pyplot import.** Chart helpers follow the `_chart(path, fig)` save pattern and return a path or `None`.

---

## 3. THE KEYSTONE GAP — net reserves are never computed

`signals/external.py:51` reads `reserves_df["net_reserves_usd_bn"]` and `sections/reserves/report.py` plots it, but **`ingestion/reserves/monthly.py::fetch_reserves()` only ever writes `reserves_usd_bn` (gross).** The net column silently never exists, so every "net reserves" number in the product is absent. Meanwhile `ingestion/reserves/balance_sheet.py` already parses **every component needed to compute net** from the weekly econ0200.pdf into `data/reserves/bcra_balance_sheet_usd.csv`.

**Fixing this is Phase 1 and unblocks the entire spine.**

The parser produces flattened USD columns like (verify exact names against a real parsed CSV):
- `ASSETS|INTERNATIONAL RESERVES|_total` — gross reserves
- `...|Gold (Net of Provisions)`, `...|Foreign Currency Deposits`, `...|Investable Foreign Currency Placements`, `...|Multilateral Credit Agreements`, `...|Derivative Instruments on International Reserves`
- `LIABILITIES|SDR ALLOCATIONS|_total`
- `LIABILITIES|REPO OBLIGATIONS|_total` (Pases — BIS/bank repos)
- `LIABILITIES|MULTILATERAL CREDIT AGREEMENT DEBTS|_total` (**the PBOC yuan swap drawn liability**)
- `LIABILITIES|OBLIGATIONS WITH INTERNATIONAL ORGANIZATIONS|_total` (IMF)
- `LIABILITIES|CURRENT ACCOUNTS IN OTHER CURRENCIES|_total` (**bank USD reserve requirements / encajes** — verify)

---

## 4. Build Phases

> Each task block: **File** · **Signature** · **Do** · **Reuse** · **Accept**. Tasks within a phase are ordered. Don't start a phase until the prior phase's acceptance tests pass.

### PHASE 1 — The Spine: compute real Net & Net-Net reserves + the waterfall

**Task 1.1 — NIR computation module**
- **File:** new `ingestion/reserves/net.py`
- **Signature:** `def compute_net_reserves() -> pd.DataFrame | None`
- **Do:** Read `data/reserves/bcra_balance_sheet_usd.csv`. For each weekly row compute three layers using a **documented formula constant** at the top of the file:
  ```
  GROSS   = INTERNATIONAL RESERVES|_total
  NIR     = GROSS - MULTILATERAL CREDIT AGREEMENT DEBTS - REPO OBLIGATIONS
                  - CURRENT ACCOUNTS IN OTHER CURRENCIES(bank FX encajes)
  NET_NET = NIR - SDR ALLOCATIONS - OBLIGATIONS WITH INTERNATIONAL ORGANIZATIONS(near-term IMF)
  ```
  Write `data/reserves/reserves_layers.csv` with columns `date, gross_usd_bn, nir_usd_bn, net_net_usd_bn` plus the individual subtracted components (for the decomposition in 1.3). Define the column→formula mapping as a dict so it's auditable and survives parser column additions. If a required column is missing, log WARNING and set that layer to NaN (never crash).
- **Reuse:** `RESERVES_DIR`, `get_logger`. **Units: the `_usd` CSV is ALREADY in USD billions — do NOT scale.** (`INTERNATIONAL RESERVES|_total` = 46.062 means $46.062B.)
- **Verified column names** (confirmed against the live CSV 2026-05-15): gross = `ASSETS|INTERNATIONAL RESERVES|_total`; swap = `LIABILITIES|MULTILATERAL CREDIT AGREEMENT DEBTS|_total` (currently 0.0 — keep it anyway); repos = `LIABILITIES|REPO OBLIGATIONS|_total`; encajes = `LIABILITIES|CURRENT ACCOUNTS IN OTHER CURRENCIES|_total` (the biggest subtraction, ~$15.7B); SDR = `LIABILITIES|SDR ALLOCATIONS|_total`; IMF = `LIABILITIES|OBLIGATIONS WITH INTERNATIONAL ORGANIZATIONS|_total`. Worked example: 46.062 − 0 − 8.098 − 15.701 = NIR 22.263; − 0.436 − 1.042 = Net-Net 20.785. Gold (`...|Gold (Net of Provisions)`) stays in NIR; make excluding it a config option, not a hardcoded choice.
- **Note:** only ~2 weekly rows exist so far (parser recently refactored) — handle <13 rows gracefully; time-series/decomposition charts stay sparse until more weeks accumulate.
- **Accept:** `reserves_layers.csv` exists; `gross > nir > net_net` for recent rows; numbers are within sane ranges (gross ~$20–45B). Print the latest row.

**Task 1.2 — Wire net into the monthly series & fetch_all**
- **File:** `ingestion/reserves/monthly.py`, `ingestion/reserves/__init__.py`, `ingestion/fetch_all.py`
- **Do:** After `fetch_reserves()` produces the monthly gross series, left-join the month-end `nir_usd_bn` / `net_net_usd_bn` from `reserves_layers.csv` (resample weekly→month-end) so `bcra_reserves.csv` gains `net_reserves_usd_bn` (= NIR) and `net_net_reserves_usd_bn`. Export `compute_net_reserves` from the package `__init__`. Call it in `fetch_all()` right after `fetch_bcra_balance_sheet()` (the balance sheet must run first — it's the input).
- **Accept:** `bcra_reserves.csv` now has a populated `net_reserves_usd_bn`; `signals/external.py` net-reserve flags fire with real numbers.

**Task 1.3 — Reserve waterfall + layers section**
- **File:** rewrite `sections/reserves/report.py` (extend, keep existing charts)
- **Do:** Add `chart_reserve_waterfall(layers_df)` — a bar-of-bars showing Gross → (−swap) → (−repos) → (−encajes) = NIR → (−SDR/IMF) = Net-Net, for the latest week vs 4 weeks ago vs 1 year ago. Add `chart_layers_timeseries(layers_df)` — gross/NIR/net-net lines, 24m, with the diverging spread shaded. Add a `formula_block` documenting the exact NIR/Net-Net definition (mandated by REPORT_BLUEPRINT §2A). Update `kpi_row` to show Gross / NIR / Net-Net / Net-Net Δ4w.
- **Reuse:** `ReservesPDF`, `_chart`, `CHART_STYLE`, existing color constants.
- **Accept:** `reserves_report.pdf` renders the waterfall with three populated layers and the formula box.

### PHASE 2 — Reserve-change decomposition (the weekly money shot)

**Task 2.1 — Weekly ΔNIR bridge data**
- **File:** new `signals/reserves.py` (new domain signal) — `def compute() -> dict`
- **Do:** From `reserves_layers.csv`, compute week-over-week and 4-week ΔNIR, and attribute the change across the parsed components (Δswap, Δrepos, Δencajes, Δgross-of-which-FX vs gold valuation). Flag **earned vs borrowed**: rises in `MULTILATERAL CREDIT AGREEMENT DEBTS` or `REPO OBLIGATIONS` are *borrowed* (WARNING flag even if gross rose). Emit metrics: `nir_change_1w`, `nir_change_4w`, `borrowed_share_pct`, plus a `decomposition` dict. Write `signals_reserves.json`.
- **Accept:** JSON validates against the schema; a week where gross rose only via repos produces a WARNING "borrowed, not earned" flag.

**Task 2.2 — Decomposition bridge chart** in `sections/reserves/report.py`: `chart_nir_bridge(signal_dict)` — trailing 13 weeks, earned (green) vs borrowed (orange) stacked. **Accept:** chart renders from `signals_reserves.json`.

### PHASE 3 — FX Regime

> **Data reality:** official FX exists (`bcra_fx.csv`). Parallels (CCL/MEP/blue), the band edges, REER, and ROFEX futures are **not on datos.gob.ar**. Source pragmatically and isolate the fragile sources.

**Task 3.1 — Parallel dollars & brecha**
- **File:** new `ingestion/fx.py` — `fetch_parallel_fx(months) -> DataFrame|None` (cols `date, ccl, mep, blue, official`).
- **Do:** CCL/MEP are computable from bond/ADR pairs (e.g. AL30/AL30D) if available on datos.gob.ar; otherwise scrape a public endpoint (e.g. dolarapi/ámbito-style JSON) via `utils.fetch_json` with caching. Compute `brecha_ccl_pct = (ccl/official - 1)*100`. **Put the chosen source URL in a single module constant and document fragility in a comment.**
- **Accept:** `data/external/fx_parallel.csv` written; brecha computed.

**Task 3.2 — REER** — `fetch_reer(months)` from BCRA's TCRM (ITCRM) series if on datos.gob.ar; else compute a bilateral real-USD index from official FX + Argentine CPI + US CPI (WorldBank). Add band-slope vs core-inflation metric. **Accept:** `reer.csv` with a percentile-vs-history column.

**Task 3.3 — FX signal** `signals/fx.py::compute()` → metrics: `brecha_ccl_pct`, `reer_percentile`, `band_position_pct` (if band config provided), flags per REPORT_BLUEPRINT §3 bull/bear. **Task 3.4** — `sections/fx/section.py` with the dollar-fan chart + REER-vs-history chart, wired into the main report.

### PHASE 4 — External flows & forward dollar calendar

**Task 4.1 — Energy trade balance split** in `ingestion/external.py` (or `production.py`): break out energy exports/imports so the structural energy-balance swing is its own series. **Task 4.2 — Forward dollar calendar:** new `signals/external_flows.py` projecting next-6-month net FX (agro liquidation seasonality + energy + tourism + scheduled debt service from Phase 5). Render as forward bars in `sections/fx` or a new external section. **Accept:** a forward-looking bar chart of projected monthly net FX.

### PHASE 5 — Anchors (mostly reuse + extend)

**Task 5.1 — Inflation last-mile:** extend `signals/inflation.py` with `core_mom`, `core_3m_annualized`, and `core_minus_band_slope` (REER drift). **Task 5.2 — Fiscal quality:** extend `signals/fiscal.py` with structural-vs-one-off revenue split and a quasi-fiscal (LEFI interest) line if data available. **Task 5.3 — Debt wall & coverage:** new `signals/debt_wall.py` reading the **hardcoded payment schedule already in `sections/debt/section.py`** (refactor it into a config constant) → compute `fx_coverage_ratio = net_net / next_12m_hardcy_payments`. **Task 5.4 — Peso curve / monetary:** `ingestion/peso_curve.py` (LECAP/CER yields if sourceable) + `signals/monetary.py` (real ex-ante rate from policy rate − REM expectations; M2-real remonetization). Mark curve/futures sources as fragile.

### PHASE 6 — Weekly mechanics (makes it a *weekly* product)

**Task 6.1 — Regime verdict ladder** (see §5 below): new `signals/regime.py::compute()` reading all signals → one of the 5 ladder rungs, with NIR-red as a hard ceiling. This **augments** `signals/master.py` (keep master for the wage-growth lens; regime is the trading lens).

**Task 6.2 — Weekly diff engine:** new `report/weekly_diff.py` — persist each run's headline metrics to `data/signals/history.jsonl` (append one row per run, keyed by date). Provide `def whats_changed() -> dict` returning Δ vs the prior run for every scorecard metric. **Accept:** second run produces non-empty diffs.

**Task 6.3 — Cover page + scorecard + "what changed" boxes:** new `report/cover.py` rendering the one-line verdict, the regime-ladder rung, the "Two Clocks" chart (NIR-vs-target left axis, core-inflation right axis), and the traffic-light scorecard. Add a `whats_changed` box helper to `ArgentinaPDF` and call it at the top of each section.

**Task 6.4 — IMF NIR target config:** new `config/imf_targets.py` (a hand-maintained dict of `{test_date: nir_floor_usd_bn}` from the EFF staff report) + `nir_vs_target` metric in `signals/reserves.py`. Document that this is manually refreshed each IMF review (like the existing hardcoded debt schedule).

### PHASE 7 — Real economy & meta-layer (lowest priority — reframe, don't rebuild)

§9–§12 signals already exist; just surface them as "political-runway context" in the report and add the "two-speed economy" chart (tradeables vs IPI) to `sections/production`. §13 political risk and §14 asset dashboard start as hand-maintained config tables (event calendar, bond price dashboard) — wire to live sources later.

---

## 5. The Regime Verdict Ladder (the trading verdict)

`signals/regime.py` outputs one rung. **Hard rule: a red NIR-vs-target caps the verdict at `FRAGILE` regardless of all other greens** (REPORT_BLUEPRINT §1).

```
BOP_CRISIS_RISK  →  FRAGILE_TARGET_MISS_WATCH  →  STABILIZING_UNCONFIRMED
   →  STABILIZATION_HOLDING_WATCH_SUSTAINABILITY  →  STRUCTURAL_TURN_CONFIRMED
```
Move up only when **both** the external clock (NIR meeting IMF target, earned not borrowed) **and** the nominal anchor (core inflation low/falling) confirm. Activity/politics can cap but not lift. Emit the `binding_constraint` (which factor is the current ceiling) every run.

---

## 6. Conventions every task must follow (beyond CLAUDE.md / CODING_CHECKLIST.md)

- **Never crash on a data gap** — return `None`, append a warning, let the report show "n/a". The pipeline must always produce PDFs.
- **Earned vs borrowed** is a first-class concept — any reserve/fiscal/credit rise sourced from repos/swaps/one-offs gets a WARNING flag, never a POSITIVE.
- **Isolate fragile sources** (parallels, futures, EMBI, NIR targets) in their own module with the source URL as a documented constant, so a broken scrape degrades one section, not the run.
- **New data dir?** add a constant to `utils`. **New series ID?** add it to `DATA_SOURCES.md` first.
- **Signal JSON schema is fixed** — match it exactly so `signals/regime.py` and the report can consume any domain uniformly.
- Reuse the `ReservesPDF` helper set for any new section PDF; don't re-implement KPI rows / formula boxes.

---

## 7. Verification (end-to-end)

After each phase:
1. `uv run python main.py --no-pdf` — confirm new `data/signals/signals_*.json` written and schema-valid.
2. `uv run python main.py` — confirm all PDFs still build (no fpdf2 Latin-1 crash, no duplicate-column header bug).
3. Spot-check the new numbers against a known reference (e.g. NIR roughly matches the figure quoted in BCRA's weekly press / consultancy estimates).

**Phase-1 done-definition (the keystone):** `bcra_reserves.csv` has a populated `net_reserves_usd_bn`; `reserves_report.pdf` shows the Gross→NIR→Net-Net waterfall with the formula box; `signals_external.json` net-reserve flags reflect real values.

**Full product done-definition:** a single weekly PDF opens with the verdict-ladder cover + Two-Clocks chart + scorecard; every section carries a "what changed this week" box; reserves decomposition distinguishes earned vs borrowed; NIR is tracked against the IMF target path.

---

## Appendix — Known series IDs (verify against `DATA_SOURCES.md`; some in that file are stale)

- Reserves (daily): `92.2_RESERVAS_IRES_0_0_32_40` · (monthly): `92.1_RID_0_0_32`
- Balance-sheet PDF: `https://www.bcra.gob.ar/archivos/Pdfs/PublicacionesEstadisticas/econ0200.pdf` (weekly; parser already handles it)
- Oil prod: `363.3_PRODUCCIONUDO__28` · Gas: `364.3_PRODUCCIoNRAL__25`
- IPI: `309.1_PRODUCCIONNAL_0_M_30` · ISAC(cement): `33.4_ISAC_CEMENAND_0_0_21_24`
- EMAE total: `143.3_NO_PR_2004_A_21` (+ sector variants in `DATA_SOURCES.md`)
- **`api.bcra.gob.ar/estadisticas` is fully deprecated — do not use.** All BCRA data via datos.gob.ar or the econ0200 PDF.
- **Not on datos.gob.ar (need external/manual sources):** CCL/MEP/blue, FX band edges, REER/ITCRM (check first), ROFEX futures, EMBI+ spread, peso-curve yields, REM expectations, IMF NIR targets, sovereign bond prices.
