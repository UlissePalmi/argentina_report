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
- `productivity_report.pdf` — deep dive: real wages, production, productivity, FBCF
- `financing_report.pdf` — deep dive: credit expansion, savings & deposits

**Verification:** all three PDFs produced + `data/signals/*.json` files written.

To force re-fetch (bypass cache), delete files from `cache/`.

## Architecture — five layers

```
Layer 1: datos.gob.ar / BCRA / WB  →  utils.fetch_json() [cache/]
Layer 2: external/fetch.py          →  data/<module>/*.csv
Layer 3: signals/*.py               →  data/signals/signals_*.json
Layer 4: .claude/SKILLS/*.md        →  LLM reads signals, writes prose
Layer 5: report/build.py            →  data/charts/*.png + data/reports/*.pdf
```

### Module structure (Layer 1–2)

All fetch logic lives in `external/fetch.py` — including GDP, CPI, employment, EMAE, production, and credit. Despite the directory name, `external/` is the catch-all fetch module (not just balance of payments data). Each domain writes a cleaned CSV to `data/<domain>/`.

The topic modules (`gdp/`, `inflation/`, `consumption/`, `production/`, `productivity/`, `financing/`) each contain `section.py` (or `report.py`) for rendering, not fetching.

### Signals layer (Layer 3)

`signals/` computes pre-aggregated analytical metrics from the CSVs and writes structured JSON to `data/signals/`. Run automatically as part of `main.py`. Each script follows the same pattern: read CSV → compute metrics + flags + trend → write JSON.

| Script | Source CSV | Output |
|---|---|---|
| `signals/wages.py` | `data/consumption/consumption.csv` | real wage YoY, trend, consecutive positive months |
| `signals/credit.py` | `data/consumption/consumption.csv` | credit-wage spread, sustainability assessment |
| `signals/investment.py` | `data/gdp/gdp_fbcf.csv` | FBCF proxy YoY, dollar-draining vs neutral split |
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

Run any skill by reading its `.md` file and the signals it references.

### Report assembler (Layer 5)

`report/build.py` owns `ArgentinaPDF` (fpdf2 subclass) and `build_report()`.
`consumption/report.py` owns `ConsumptionPDF` (subclass of `ArgentinaPDF`) and builds the productivity deep-dive.
`financing/report.py` builds the financing deep-dive.

## Key conventions

**Real series**: Fisher-adjusted only — `((1 + nominal/100) / (1 + CPI/100) - 1) * 100`. Never simple subtraction. Implemented in `external/fetch.py::compute_real_values()`.

**PDF text safety**: All strings passed to fpdf2 go through `_safe()` in `report/build.py`. fpdf2 uses Latin-1; em-dashes and smart quotes will throw `FPDFUnicodeEncodingException`.

**Charts**: `matplotlib.use("Agg")` must be called before any pyplot import. Already done in all section modules — preserve it when adding new chart functions.

**Column naming**: Real YoY credit columns = `real_<category>_pct`; MoM = `real_<category>_mom_pct`. When building PDF tables, rename to short labels that don't share any name with an existing column (fpdf2 quirk: duplicate column names cause header to render as a data row).

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
- **BCRA API** — `https://api.bcra.gob.ar/estadisticas/v3.0/monetarias/<variable_id>`
- **World Bank** — `https://api.worldbank.org/v2/country/ARG/indicator/<indicator_id>`

All HTTP responses cached in `cache/` as JSON (key = URL + params). `utils.fetch_json()` handles retry + cache for all fetch modules.
