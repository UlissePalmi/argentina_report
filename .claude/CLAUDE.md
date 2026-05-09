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
- `argentina_macro_report.pdf` — main report (external, inflation, fiscal, debt, GDP, production, labor, consumption)
- `productivity_report.pdf` — deep dive: real wages, GDP composition, production, productivity, FBCF
- `financing_report.pdf` — deep dive: credit expansion, savings & deposits

**Verification:** all three PDFs produced + `data/signals/*.json` files written.

To force re-fetch (bypass cache), delete files from `cache/`.

## Architecture — five layers

```
Layer 1: datos.gob.ar / WB / IMF     →  utils.fetch_json() [cache/]
Layer 2: external/<topic>.py          →  data/external/*.csv  (and data/<module>/*.csv)
Layer 3: signals/*.py                 →  data/signals/signals_*.json
Layer 4: .claude/SKILLS/*.md          →  LLM reads signals, writes prose
Layer 5: report/build.py              →  data/charts/*.png + data/reports/*.pdf
```

### Module structure (Layer 1–2)

`external/fetch.py` is a **re-export hub only** — it imports and re-exports all public functions from the topic modules below. Add new fetch functions to the appropriate topic module, then re-export from `fetch.py` and add to `__all__`. `external/debt.py` is imported directly in `main.py` (not via `fetch.py`).

**BCRAClient is removed.** `api.bcra.gob.ar/estadisticas` is fully deprecated (all v1/v2/v3). All reserve and credit data now comes exclusively from datos.gob.ar.

| Module | Fetches |
|---|---|
| `external/client.py` | Shared HTTP clients: `DatosClient`, `WorldBankClient`, `_start()` |
| `external/reserves.py` | BCRA reserves (datos.gob.ar), exchange rate, current account, trade balance, external debt |
| `external/fiscal.py` | Monthly IMIG primary + financial balance (ARS bn + % GDP); `_build_gdp_monthly()` for normalisation |
| `external/debt.py` | Govt external liability breakdown (INDEC IIP quarterly); WB debt service ratios |
| `external/gdp.py` | GDP growth, expenditure components (real + nominal), EMAE, FBCF breakdown |
| `external/inflation.py` | INDEC CPI |
| `external/consumption.py` | Wages, credit (6 categories), deposits; `compute_real_values()` |
| `external/production.py` | IPI (EMAE industria proxy), oil/gas, ISAC, agriculture |
| `external/productivity.py` | SIPA employment, UCII (via direct CSV download), productivity + ULC |

UCII is fetched by downloading the full INDEC distribution CSV directly (`infra.datos.gob.ar/catalog/sspm/dataset/31/distribution/31.3/...`) because the sector-level series were removed from the datos.gob.ar API.

### Fiscal % GDP normalisation

`external/fiscal.py::_build_gdp_monthly()` builds the monthly GDP denominator with two sources tried in order:

1. **Primary**: INDEC quarterly nominal GDP (`166.2_PPIB_0_0_3`, datos.gob.ar). Values are **annualized quarterly rates** in millions of ARS current prices (i.e. each quarterly value is already annual-rate; average of four quarters = WB annual figure). Each quarter's value is assigned to its 3 calendar months.
2. **Fallback**: World Bank `NY.GDP.MKTP.CN` (annual), interpolated monthly.

For months beyond the last published quarter (WB typically lags ~1 year; INDEC quarterly lags ~2 quarters), the series is extended using the INDEC CPI index (`data/inflation/indec_cpi.csv`) scaled from the reference point at December of the last known year. CPI scaling is only applied to months **after** the last WB/INDEC year — within the last known year, the flat annual-rate is used as-is.

Formula: `fiscal_*_pct_gdp = (monthly_ars_bn / (annualized_gdp_bn / 12)) * 100`

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
| `signals/fiscal.py` | `data/external/fiscal_balance.csv` | surplus streak, trend, YTD, 12m rolling, % GDP |
| `signals/production.py` | `data/production/production_monthly.csv` | IPI, oil/gas, Vaca Muerta signal |
| `signals/labor.py` | `data/productivity/employment.csv` + `productivity.csv` | SIPA employment, ULC, productivity trend |
| `signals/master.py` | All above signals | Verdict + scorecard (reads from `data/signals/*.json`) |

Every signal JSON has the same structure: `domain`, `as_of_date`, `data_quality`, `metrics{}`, `flags[]`, `trend`, `connection_to_master_variable`, `summary`.

`signals/master.py` outputs the **verdict** — one of: `crisis_risk`, `fragile_recovery`, `structural_improvement_underway_unconfirmed`, `recovery_confirmed_watch_sustainability`, `sustainable_growth`.

### Sections (Layer 5 rendering)

All section renderers live in `sections/<domain>/section.py`. Each exposes the standard interface:

```python
def build_pdf_section(pdf: ArgentinaPDF, data: dict) -> None: ...
def build_md_section(data: dict) -> str: ...
```

| Section | Data key passed in | Key output |
|---|---|---|
| `sections/fiscal/section.py` | `fiscal_df` | Monthly bar chart + annual summary table (2023 baseline) + signal callout |
| `sections/debt/section.py` | `debt_df` | Stacked bar (bonds vs loans/multilaterals) + debt service % exports + hardcoded payment schedule |
| `sections/gdp/section.py` | `gdp_df`, `components_df`, `nominal_df`, `fbcf_df`, `emae_df` | Composition pies, FBCF breakdown |
| `sections/inflation/section.py` | `cpi_df` | MoM/YoY chart |
| `sections/production/section.py` | `production_df`, `agro_df` | IPI, oil/gas, ISAC charts |
| `sections/labor/section.py` | `consumption_df`, `employment_df` | Real wages, SIPA employment |
| `sections/consumption/section.py` | `consumption_df` | Credit, deposits |

`sections/debt/section.py` contains a **hardcoded payment schedule** (2025–2028) sourced from Secretaría de Finanzas Q4-2025 report and IMF SBA term sheet. It is labeled with a "last updated" date and must be refreshed manually when Finanzas publishes a new quarterly report.

The two deep-dive reports use their own PDF subclasses:
- `sections/consumption/report.py` — `ConsumptionPDF` (subclass of `ArgentinaPDF`); builds `productivity_report.pdf`
- `sections/financing/report.py` — builds `financing_report.pdf`

`report/build.py` owns `ArgentinaPDF`, `_safe()`, and `build_report()`. Section order in the main report: External → Inflation → Fiscal → Debt → GDP → Production → Labor → Consumption.

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

## Key conventions

**Real series**: Fisher-adjusted only — `((1 + nominal/100) / (1 + CPI/100) - 1) * 100`. Never simple subtraction. Implemented in `external/consumption.py::compute_real_values()`.

**GDP share column naming**:
- `C_share_real`, `G_share_real`, etc. — constant 2004 prices (chain-linked; may not sum to 100%)
- `C_share_nom`, `G_share_nom`, etc. — current prices (nominal; use for structural analysis)
- `C_pct`, `G_pct`, etc. — YoY growth rates (always from constant-price series)

**PDF text safety**: All strings passed to fpdf2 go through `_safe()` in `report/build.py`. fpdf2 uses Latin-1; em-dashes and smart quotes will throw `FPDFUnicodeEncodingException`. Never use `%q` in `strftime()` — it is not a valid format code.

**Charts**: `matplotlib.use("Agg")` must be called before any pyplot import. Already done in all section modules — preserve it when adding new chart functions.

**Column naming for tables**: When building PDF tables, rename columns to short labels that don't share any name with an existing column (fpdf2 quirk: duplicate column names cause header to render as a data row).

**Signal script interface** — every `signals/*.py` exposes:
```python
def compute() -> dict: ...  # returns the signal dict and writes JSON to data/signals/
```

## Data sources

- **datos.gob.ar** — `https://apis.datos.gob.ar/series/api/series/?ids=<id>&limit=<n>&collapse=month`
  - Constant-price (real) quarterly series: `4.2_` prefix
  - Current-price (nominal) quarterly series: `4.4_` prefix
  - INDEC IIP (International Investment Position): `144.4_` series (quarterly, USD millions)
  - Search endpoint: `https://apis.datos.gob.ar/series/api/search/?q=<query>&limit=10`
- **World Bank** — `https://api.worldbank.org/v2/country/ARG/indicator/<indicator_id>`
- **BCRA API** — fully deprecated; do not use `api.bcra.gob.ar/estadisticas`

All HTTP responses cached in `cache/` as JSON (key = URL + params). `utils.fetch_json()` handles retry + cache for all fetch modules.

When a datos.gob.ar series returns all nulls or is not found, the series has likely been removed from the API. Check whether the underlying INDEC distribution CSV still has the data — this is how UCII sector data was recovered.
