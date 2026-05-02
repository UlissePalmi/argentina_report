# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## On every new session, read in this order
1. `.claude/BLUEPRINT.md` — project mission, master variable framework, layer definitions
2. `.claude/DATA_SOURCES.md` — all series IDs, API endpoints, file locations
3. `.claude/SKILLS/` — interpretation frameworks for each analytical domain

## Running the pipeline

```bash
uv run python main.py
```

Fetches all data, computes signals, generates charts, and writes three PDFs to `data/reports/`:
- `argentina_macro_report.pdf` — main report (external, inflation, GDP, consumption)
- `productivity_report.pdf` — deep dive: real wages, GDP composition, production, productivity, FBCF
- `financing_report.pdf` — deep dive: credit expansion, savings & deposits

**Verification:** all three PDFs produced + `data/signals/*.json` files written.

To force re-fetch (bypass cache), delete files from `cache/`.

## Architecture — five layers

```
Layer 1: datos.gob.ar / BCRA / WB  →  utils.fetch_json() [cache/]
Layer 2: external/<topic>.py        →  data/<module>/*.csv
Layer 3: signals/*.py               →  data/signals/signals_*.json
Layer 4: .claude/SKILLS/*.md        →  LLM reads signals, writes prose
Layer 5: report/build.py            →  data/charts/*.png + data/reports/*.pdf
```

### Module structure (Layer 1–2)

`external/fetch.py` is a **re-export hub only** — it imports and re-exports all public functions from the topic modules below. Add new fetch functions to the appropriate topic module, then re-export from `fetch.py` and add to `__all__`.

| Module | Fetches |
|---|---|
| `external/client.py` | Shared HTTP clients: `DatosClient`, `BCRAClient`, `WorldBankClient`, `_start()` |
| `external/reserves.py` | BCRA reserves, exchange rate, current account, trade balance, external debt |
| `external/gdp.py` | GDP growth, expenditure components (real + nominal), EMAE, FBCF breakdown |
| `external/inflation.py` | INDEC CPI |
| `external/consumption.py` | Wages, credit (6 categories), deposits; `compute_real_values()` |
| `external/production.py` | IPI (EMAE industria proxy), oil/gas, ISAC, agriculture |
| `external/productivity.py` | SIPA employment, UCII (via direct CSV download), productivity + ULC |

UCII is fetched by downloading the full INDEC distribution CSV directly (`infra.datos.gob.ar/catalog/sspm/dataset/31/distribution/31.3/...`) because the sector-level series were removed from the datos.gob.ar API.

The topic render modules (`gdp/`, `inflation/`, `consumption/`, `production/`, `productivity/`, `financing/`) each contain `section.py` or `report.py` for rendering, not fetching.

### GDP data files

| File | Contents |
|---|---|
| `data/gdp/gdp_components.csv` | Constant-2004-price YoY growth (`C_pct` etc.) + real shares (`C_share_real` etc.) |
| `data/gdp/gdp_nominal.csv` | Nominal (current-price) shares: `C_share_nom`, `G_share_nom`, `I_share_nom`, `NX_share_nom` |
| `data/gdp/gdp_fbcf.csv` | FBCF sub-components: construction, domestic machinery, imported machinery, transport — share of FBCF + YoY growth |
| `data/gdp/emae.csv` | Monthly EMAE headline + 7 sector indices |
| `data/gdp/wb_gdp_growth.csv` | Quarterly GDP YoY growth |

`gdp_nominal.csv` uses `4.4_` series (current prices). `gdp_components.csv` uses `4.2_` series (constant 2004 prices). The two diverge significantly — use nominal for structural share analysis, real for YoY growth rates. Never mix them.

FBCF dollar classification: Construction + domestic machinery = **dollar-neutral**; imported machinery + transport = **dollar-draining**.

### Signals layer (Layer 3)

`signals/` computes pre-aggregated analytical metrics from the CSVs and writes structured JSON to `data/signals/`. Run automatically as part of `main.py`.

| Script | Source CSV | Output |
|---|---|---|
| `signals/wages.py` | `data/consumption/consumption.csv` | real wage YoY, trend, consecutive positive months |
| `signals/credit.py` | `data/consumption/consumption.csv` | credit-wage spread, sustainability assessment |
| `signals/investment.py` | `data/gdp/gdp_fbcf.csv` | FBCF sub-component YoY, dollar-draining vs neutral split |
| `signals/inflation.py` | `data/inflation/indec_cpi.csv` | MoM trend, disinflation confirmation |
| `signals/external.py` | `data/external/*.csv` | reserves, current account, FX trend |
| `signals/production.py` | `data/production/production_monthly.csv` | IPI, oil/gas, Vaca Muerta signal |
| `signals/labor.py` | `data/productivity/employment.csv` + `productivity.csv` | SIPA employment, ULC, productivity trend |
| `signals/master.py` | All above signals | Verdict + scorecard (reads from `data/signals/*.json`) |

Every signal JSON has the same structure: `domain`, `as_of_date`, `data_quality`, `metrics{}`, `flags[]`, `trend`, `connection_to_master_variable`, `summary`.

`signals/master.py` outputs the **verdict** — one of: `crisis_risk`, `fragile_recovery`, `structural_improvement_underway_unconfirmed`, `recovery_confirmed_watch_sustainability`, `sustainable_growth`.

### Skills (Layer 4)

Skills are markdown prompts in `.claude/SKILLS/`. They instruct Claude to read signal JSON files and write analytical prose. They do no arithmetic — all numbers come pre-computed from Layer 3.

| Skill file | Purpose |
|---|---|
| `SKILL_master.md` | Executive summary + closing synthesis using `signals_master.json` |
| `SKILL_labor.md` | Real wages + formal employment + productivity-backing test |
| `SKILL_investment.md` | FBCF sub-components, dollar tension, mortgage contradiction test |
| `SKILL_inflation.md` | Disinflation trajectory, MoM thresholds, connection to purchasing power |
| `SKILL_production.md` | IPI, Vaca Muerta signal, two-speed economy test |
| `interpret-gdp.md` | GDP composition (Y = C+I+G+NX), growth drivers |
| `interpret-consumption.md` | Three-driver framework: wage-led / credit-led / savings drawdown |
| `interpret-ca.md` | External position: CA, reserves, trade balance, FX |

### Report assembler (Layer 5)

`report/build.py` owns `ArgentinaPDF` (fpdf2 subclass) and `build_report()`.
`consumption/report.py` owns `ConsumptionPDF` (subclass of `ArgentinaPDF`) and builds the productivity deep-dive. Its GDP composition section delegates entirely to `gdp.section.build_pdf_section()`.
`financing/report.py` builds the financing deep-dive.

The productivity report (`productivity_report.pdf`) includes: executive summary, GDP composition (nominal + real + FBCF breakdown), real wages, production, productivity/ULC. Pass `consumption_df` into the GDP section data dict to enable the mortgage vs. construction FBCF contradiction check.

## Key conventions

**Real series**: Fisher-adjusted only — `((1 + nominal/100) / (1 + CPI/100) - 1) * 100`. Never simple subtraction. Implemented in `external/consumption.py::compute_real_values()`.

**GDP share column naming**:
- `C_share_real`, `G_share_real`, etc. — constant 2004 prices (chain-linked; may not sum to 100%)
- `C_share_nom`, `G_share_nom`, etc. — current prices (nominal; use for structural analysis)
- `C_pct`, `G_pct`, etc. — YoY growth rates (always from constant-price series)

**PDF text safety**: All strings passed to fpdf2 go through `_safe()` in `report/build.py`. fpdf2 uses Latin-1; em-dashes and smart quotes will throw `FPDFUnicodeEncodingException`.

**Charts**: `matplotlib.use("Agg")` must be called before any pyplot import. Already done in all section modules — preserve it when adding new chart functions.

**Column naming for tables**: When building PDF tables, rename columns to short labels that don't share any name with an existing column (fpdf2 quirk: duplicate column names cause header to render as a data row).

**Section builder interface** — every `section.py` exposes:
```python
def build_pdf_section(pdf: ArgentinaPDF, data: dict) -> None: ...
def build_md_section(data: dict) -> str: ...
```

**Signal script interface** — every `signals/*.py` exposes:
```python
def compute() -> dict: ...  # returns the signal dict and writes JSON to data/signals/
```

## Data sources

- **datos.gob.ar** — `https://apis.datos.gob.ar/series/api/series/?ids=<id>&limit=<n>&collapse=month`
  - Constant-price (real) quarterly series: `4.2_` prefix
  - Current-price (nominal) quarterly series: `4.4_` prefix
  - Search endpoint: `https://apis.datos.gob.ar/series/api/series/search/?q=<query>&limit=10`
- **BCRA API** — `https://api.bcra.gob.ar/estadisticas/v3.0/monetarias/<variable_id>`
- **World Bank** — `https://api.worldbank.org/v2/country/ARG/indicator/<indicator_id>`

All HTTP responses cached in `cache/` as JSON (key = URL + params). `utils.fetch_json()` handles retry + cache for all fetch modules.

When a datos.gob.ar series returns all nulls or is not found, the series has likely been removed from the API. Check whether the underlying INDEC distribution CSV still has the data — this is how UCII sector data was recovered.
