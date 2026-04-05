# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the pipeline

```bash
uv run python main.py
```

This fetches all data, generates charts, and writes three PDFs to `data/reports/`:
- `argentina_macro_report.pdf` — main report (external, inflation, GDP, consumption overview)
- `productivity_report.pdf` — deep dive: Executive Summary, Real Wages, Production, Productivity
- `financing_report.pdf` — deep dive: Credit Expansion + Savings & Deposits

There are no tests. The verification step is running the full pipeline and confirming all three PDFs are produced with "all 10 datasets succeed" in the log output.

To re-fetch data (bypass cache), delete files from `cache/`.

## Architecture

The pipeline is a linear fetch → compute → render flow with no web server or database.

### Module structure

Each topic module (`external/`, `gdp/`, `inflation/`, `consumption/`, `production/`, `productivity/`, `financing/`) contains:
- `fetch.py` — pulls from datos.gob.ar / BCRA / World Bank, caches JSON responses, saves cleaned CSV to `data/<module>/`
- `section.py` (or `report.py`) — renders into PDF sections and generates PNG charts to `data/charts/`
- `__init__.py` — empty

The `report/build.py` assembler owns `ArgentinaPDF` (fpdf2 subclass) and `build_report()`, which calls each module's `build_pdf_section()` / `build_md_section()` in order to produce the main report.

The two deep-dive reports (`productivity_report.pdf`, `financing_report.pdf`) are built by `consumption/report.py` and `financing/report.py` respectively, which use `ConsumptionPDF` (a subclass of `ArgentinaPDF` defined in `consumption/report.py`).

### Data flow

```
datos.gob.ar / BCRA / WB  →  utils.fetch_json() [cache/]
    ↓
module/fetch.py            →  data/<module>/*.csv
    ↓
module/section.py          →  data/charts/*.png  →  data/reports/*.pdf
```

### utils.py

Central shared module. Owns:
- All directory constants (`ROOT`, `CACHE_DIR`, `DATA_DIR`, `GDP_DIR`, `EXTERNAL_DIR`, `INFLATION_DIR`, `CONSUMPTION_DIR`, `PRODUCTION_DIR`, `PRODUCTIVITY_DIR`, `CHARTS_DIR`, `REPORTS_DIR`) — all created on import
- `fetch_json()` — GET with retry + cache; all fetch modules use this exclusively
- `get_logger()` — standard logger factory

### Key conventions

**Real series**: All `real_*` columns are Fisher-adjusted: `((1 + nominal/100) / (1 + CPI/100) - 1) * 100`. Never use simple subtraction. This is done in `consumption/fetch.py::compute_real_values()`.

**PDF text safety**: All strings passed to fpdf2 must go through `_safe()` (defined in `report/build.py`) to replace em-dashes and other non-Latin-1 characters. fpdf2 uses Latin-1 encoding by default and will throw `FPDFUnicodeEncodingException` otherwise.

**Charts**: `matplotlib.use("Agg")` must be called before pyplot imports in any module that generates charts (non-interactive backend for headless rendering).

**Column naming**: Credit YoY columns follow the pattern `real_<category>_pct` (e.g. `real_personal_loans_pct`); MoM follow `real_<category>_mom_pct`. When displaying in tables, rename to short labels that don't overlap with any existing column name to avoid fpdf2 rendering the column header as a data cell.

### Section builder interface

Each `section.py` exposes:
```python
def build_pdf_section(pdf: ArgentinaPDF, data: dict) -> None: ...
def build_md_section(data: dict) -> str: ...
```

The `data` dict keys match the DataFrame names for that module.

## Slash commands (skills)

Three analytical skills are defined in `.claude/commands/`:

| Command | Reads | Produces |
|---|---|---|
| `/interpret-consumption` | `data/consumption/consumption.csv`, `data/inflation/indec_cpi.csv`, `data/gdp/gdp_components.csv` | Prose analysis of consumption drivers (3 configurations: wage-led, credit-led, savings drawdown) |
| `/interpret-gdp` | `data/gdp/gdp_components.csv`, `data/gdp/wb_gdp_growth.csv`, `data/gdp/emae.csv` | GDP composition analysis (Y = C + I + G + NX) |
| `/interpret-ca` | `data/external/imf_current_account.csv`, `data/external/indec_trade.csv`, `data/external/bcra_reserves.csv`, `data/external/bcra_fx.csv` | External/dollar situation analysis |

Run these after `main.py` to generate analytical prose from the freshly fetched data.

## Data sources

- **datos.gob.ar** — INDEC and BCRA series; queried via `https://apis.datos.gob.ar/series/api/series/?ids=<series_id>&limit=<n>&collapse=month`
- **BCRA API** — `https://api.bcra.gob.ar/estadisticas/v3.0/monetarias/<variable_id>`
- **World Bank** — `https://api.worldbank.org/v2/country/ARG/indicator/<indicator_id>`

All responses are cached in `cache/` as JSON files (key derived from URL + params). Delete cache files to force a re-fetch.
