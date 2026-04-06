# Argentina Macro Research Pipeline — Master Blueprint

## PROJECT MISSION
Build a repeatable, automated macro research pipeline that answers 
one central question every time it runs:

"Is Argentina building the conditions for sustainable real wage 
growth, or is it just going through another temporary recovery 
that will reverse?"

Every piece of code, every data series, every analytical section 
exists to answer this question. If a new feature doesn't connect 
to this question, don't build it.

---

## DIRECTORY STRUCTURE

/argentina-macro/
│
├── main.py                    # Single entry point — runs everything
├── requirements.txt
├── config.py                  # All constants, thresholds, API URLs
├── README.md
│
├── /data/
│   ├── /raw/                  # Untouched API responses and downloads
│   │   ├── indec_.csv
│   │   ├── bcra_.csv
│   │   ├── energia_.csv
│   │   └── imf_.csv
│   ├── /processed/            # Cleaned, deflated, merged series
│   │   ├── wages.csv
│   │   ├── credit.csv
│   │   ├── gdp_expenditure.csv
│   │   ├── gdp_production.csv
│   │   ├── fbcf_breakdown.csv
│   │   ├── external.csv
│   │   ├── inflation.csv
│   │   ├── employment.csv
│   │   └── energy.csv
│   └── /signals/              # Pre-computed analytical signals
│       ├── signals_wages.json
│       ├── signals_credit.json
│       ├── signals_investment.json
│       ├── signals_external.json
│       ├── signals_production.json
│       ├── signals_inflation.json
│       ├── signals_labor.json
│       └── signals_master.json
│
├── /src/
│   ├── /fetch/                # Layer 1: Raw data ingestion
│   │   ├── fetch_indec.py
│   │   ├── fetch_bcra.py
│   │   ├── fetch_energia.py
│   │   ├── fetch_labor.py
│   │   └── fetch_imf.py
│   ├── /process/              # Layer 2: Cleaning and transformation
│   │   ├── deflate.py         # Fisher equation, all real series
│   │   ├── gdp_processor.py   # Shares, contributions, FBCF breakdown
│   │   ├── validate.py        # Sum checks, NaN flags, outliers
│   │   └── merge.py           # Combine series into unified datasets
│   ├── /signals/              # Layer 3: Signal computation
│   │   ├── signals_wages.py
│   │   ├── signals_credit.py
│   │   ├── signals_investment.py
│   │   ├── signals_external.py
│   │   ├── signals_production.py
│   │   ├── signals_inflation.py
│   │   ├── signals_labor.py
│   │   └── signals_master.py
│   └── /report/               # Layer 5: Report assembly
│       ├── build_report.py
│       ├── charts.py
│       └── templates/
│           └── report_template.md
│
├── /.claude/
│   ├── CLAUDE.md              # Init file — read first every session
│   ├── BLUEPRINT.md           # Project architecture and standards
│   ├── DATA_SOURCES.md        # All series, API endpoints, file locations
│   └── /skills/               # Layer 4: LLM interpretation prompts
│       ├── SKILL_master.md
│       ├── SKILL_labor.md
│       ├── SKILL_consumption.md
│       ├── SKILL_investment.md
│       ├── SKILL_external.md
│       ├── SKILL_production.md
│       └── SKILL_inflation.md
│
├── /output/                   # Final report output
│   ├── argentina_macro_report.md
│   ├── argentina_macro_report.pdf
│   └── /charts/               # All charts as PNG files
│
└── /cache/                    # Cached API responses
    └── *.json

---

## THE MASTER VARIABLE FRAMEWORK

This framework governs ALL analytical interpretation.
Every skill, every section, every conclusion must connect to it.

MASTER VARIABLE: Real productivity-backed wage growth
= The only sustainable path to rising living standards
LEVEL 1 — MASTER VARIABLE (the goal)
└── Real wage growth YoY > 0, sustained 3+ quarters
backed by productivity gains not credit
LEVEL 2 — DRIVERS (what causes it)
├── Investment (FBCF) growing → more capital per worker
├── Formal employment growing → more workers in productive jobs
├── Productivity rising → EMAE output / SIPA employment
└── Credit IN LINE with wage growth → not credit-financed
LEVEL 3 — ENABLERS (what removes constraints)
├── Inflation falling → wages not eroded monthly
├── Fiscal surplus → no crisis risk wiping out gains
├── Net reserves positive → no devaluation-inflation spiral
└── External sustainability → no balance of payments crisis
LEVEL 4 — ARGENTINA ACCELERATORS (structural transformation)
├── Vaca Muerta → permanent dollar solution
├── RIGI investment → FDI bringing capital + technology
└── Energy self-sufficiency → removes import drain

**VERDICT SCALE** (signals_master.py must output one of these):

"crisis_risk" → Wages negative + investment falling + reserves depleting
"fragile_recovery" → Wages positive but credit-driven + investment weak
"structural_improvement_underway_unconfirmed" → Enablers fixed + drivers building + wages still negative → CURRENT STATUS as of Q4 2025
"recovery_confirmed_watch_sustainability" → Wages positive 3+ quarters + investment rising + credit moderate
"sustainable_growth" → All four levels positive and self-reinforcing

---

## LAYER 1: DATA INGESTION

See DATA_SOURCES.md for full list of series, API endpoints, 
and file locations. When adding new data sources, update 
DATA_SOURCES.md first, then add the fetch function to the 
appropriate fetch_*.py file.

## LAYER 2: DATA PROCESSING RULES

### Rule 1: Always deflate nominal peso series
Use the Fisher equation — never simple subtraction.
```python
def to_real(nominal_yoy_pct: float, cpi_yoy_pct: float) -> float:
    """
    Convert nominal YoY % to real YoY %
    Inputs are percentages e.g. 430.6, 84.0
    ALWAYS use this — never nominal minus CPI
    Simple subtraction is inaccurate at Argentina's inflation levels
    e.g. 430% nominal, 84% CPI: simple=346%, Fisher=188%
    """
    nominal = nominal_yoy_pct / 100
    cpi = cpi_yoy_pct / 100
    real = ((1 + nominal) / (1 + cpi)) - 1
    return real * 100
```

### Rule 2: Always compute both YoY and MoM
For every series compute:
- `_yoy`: year-on-year % change (12-month comparison)
- `_mom`: month-on-month % change (sequential)
- `_mom_real`: MoM deflated by monthly CPI change
- `_trend_3m`: 3-month rolling average of MoM

MoM is more timely. YoY is more stable.
**When they diverge, MoM is the leading signal.**

### Rule 3: Series that need deflation vs series that don't

**DEFLATE (nominal pesos):**
- Wages, credit, deposits, any peso-denominated series

**DO NOT DEFLATE (already real or in dollars):**
- EMAE (index, already volume)
- GDP constant price series (already deflated by INDEC)
- Trade balance in USD
- Current account in USD
- Reserves in USD
- CPI itself

### Rule 4: GDP composition — always use current prices for shares
Constant price shares (Cuadro 3/11) are distorted by base year.
Use nominal current price shares (Cuadro 11) as primary.
Keep constant price growth rates (Cuadro 2) for growth analysis.
Label clearly in all outputs which is which.

### Rule 5: Handle NaN and missing data explicitly
```python
def validate_series(df, series_name, critical=True):
    nan_count = df[series_name].isna().sum()
    if nan_count > 0:
        if critical:
            raise Warning(f"CRITICAL: {series_name} has {nan_count} NaN values")
        else:
            print(f"NOTE: {series_name} has {nan_count} NaN values — use with caution")
    # Check for data gaps > 2 months
    # Check for implausible values (>500% YoY or <-90%)
```

### Rule 6: Cache all raw data
```python
CACHE_DURATION_DAYS = 7  # Re-fetch after 7 days
# Store in /cache/[source]_[series]_[date].json
# Never re-fetch if valid cache exists
```

---

## LAYER 3: SIGNAL COMPUTATION

Each signals file must output a JSON with this structure:
```python
{
    "domain": "wages",  # which domain
    "as_of_date": "2025-12-01",  # most recent data point
    "data_quality": "good/partial/poor",
    
    "metrics": {
        # All pre-computed numbers the LLM needs
        # No raw data — only analytical metrics
    },
    
    "flags": [
        # List of strings, each starting with:
        # "CRITICAL:" — requires immediate mention in report
        # "WARNING:" — should be mentioned
        # "NOTE:" — informational
        # "POSITIVE:" — highlight as good signal
    ],
    
    "trend": "improving/deteriorating/stable/mixed",
    
    "connection_to_master_variable": "positive/negative/neutral",
    
    "summary": "One sentence plain English summary"
}
```

### signals_master.py — the most important file
```python
def compute_master_signals(all_signals: dict) -> dict:
    """
    Reads all domain signal files and computes the master verdict.
    This is the file the master skill reads.
    """
    
    # Master variable assessment
    real_wage_yoy = all_signals["wages"]["metrics"]["real_wage_yoy_latest"]
    real_wage_trend = all_signals["wages"]["metrics"]["real_wage_trend_3m"]
    
    # Driver assessment  
    investment_yoy = all_signals["investment"]["metrics"]["fbcf_yoy_latest"]
    formal_emp_yoy = all_signals["labor"]["metrics"]["sipa_yoy_latest"]
    productivity_trend = all_signals["production"]["metrics"]["productivity_trend"]
    credit_wage_spread = all_signals["credit"]["metrics"]["credit_wage_spread_3m"]
    
    # Enabler assessment
    inflation_monthly = all_signals["inflation"]["metrics"]["cpi_mom_latest"]
    inflation_trend = all_signals["inflation"]["metrics"]["trend_6m"]
    fiscal_balance = all_signals["external"]["metrics"]["fiscal_balance_pct_gdp"]
    net_reserves = all_signals["external"]["metrics"]["net_reserves_bn"]
    
    # Accelerator assessment
    oil_production_yoy = all_signals["production"]["metrics"]["oil_yoy_latest"]
    energy_trade_balance = all_signals["external"]["metrics"]["energy_trade_balance_bn"]
    
    # Compute verdict
    verdict = compute_verdict(
        real_wage_yoy, investment_yoy, net_reserves, inflation_trend
    )
    
    return {
        "domain": "master",
        "verdict": verdict,
        "master_variable": {
            "value": real_wage_yoy,
            "trend": real_wage_trend,
            "status": "positive" if real_wage_yoy > 0 else "negative"
        },
        "drivers": {
            "investment": investment_yoy,
            "formal_employment": formal_emp_yoy,
            "productivity": productivity_trend,
            "credit_discipline": "good" if credit_wage_spread < 30 else "warning"
        },
        "enablers": {
            "inflation": inflation_monthly,
            "fiscal": fiscal_balance,
            "reserves": net_reserves,
        },
        "accelerators": {
            "oil_production_yoy": oil_production_yoy,
            "energy_trade_balance": energy_trade_balance,
        },
        "flags": compute_all_flags(all_signals),
        "summary": generate_summary(verdict, all_signals)
    }
```

---

## LAYER 4: SKILLS

Skills are markdown files in /.claude/SKILLS/. 
They are prompts given to an LLM to interpret the signal files.
They do NOT do math. They read pre-computed signals and write analysis.

### Skill file standard format
```markdown
# SKILL: [Domain Name]

## Purpose
[One paragraph: what this skill analyzes and why it matters]

## Data to read
- /data/signals/signals_[domain].json
- Key metrics to focus on: [list the 3-5 most important]

## Connection to master variable
[How does this domain connect to sustainable real wage growth?]
[Always end the section by making this connection explicit]

## Interpretation rules

### Thresholds
[Specific numbers that trigger different interpretations]

### Key relationships to identify
[What combinations of metrics tell important stories]

### Base effect warning
[When YoY numbers are distorted by unusual prior period]
[Always check MoM to confirm YoY signal]

## Report section format
- Length: [X paragraphs]
- Charts to reference: [which charts]
- Lead with: [most important metric]
- Always include: [what must never be omitted]
- Connect to: [which other sections to reference]

## Verdict options
[Good/neutral/concerning/critical patterns]
```

### SKILL_master.md — the synthesis skill
```markdown
# SKILL: MASTER SYNTHESIS

## Purpose
Synthesize all domain analyses into a single verdict on whether
Argentina is building conditions for sustainable real wage growth.
This is the first and last section of the report.

## Data to read
- /data/signals/signals_master.json (primary)
- All other signals files (for supporting evidence)

## The four questions (answer all four explicitly)

1. MASTER VARIABLE: Are real wages positive and trending up?
   - Current value?
   - 3-month trend?
   - Is growth backed by productivity or credit?

2. DRIVERS: Is productive capacity being built?
   - Is investment growing in the right components?
     (machinery > housing for productivity)
   - Is formal employment expanding?
   - Is output per worker rising?

3. ENABLERS: Is the macro environment stable enough?
   - Is inflation on a clear downward path?
   - Is the fiscal surplus being maintained?
   - Are reserves improving or depleting?
   - Is the external position sustainable?

4. ACCELERATORS: Is the structural transformation on track?
   - Is Vaca Muerta production growing?
   - Is the energy trade surplus expanding?
   - Are RIGI investments materializing?

## Verdict framework
Output exactly one of these verdicts with justification:

"CRISIS RISK" — if any of:
  - Real wages negative + investment falling + reserves < -$5B
  - Current account deficit > $5B/quarter with no financing
  
"FRAGILE RECOVERY" — if:
  - Real wages positive but entirely credit-driven
  - Investment weak or falling
  - Enablers still fragile

"STRUCTURAL IMPROVEMENT UNDERWAY — UNCONFIRMED" — if:
  - Enablers fixed (inflation falling, fiscal surplus, reserves improving)
  - Drivers building (investment was growing, employment rising)
  - But master variable (real wages) not yet sustainably positive
  - CURRENT STATUS as of Q4 2025

"RECOVERY CONFIRMED — WATCH SUSTAINABILITY" — if:
  - Real wages positive for 3+ consecutive quarters
  - Backed by productivity not just credit
  - Investment rising in productive components

"SUSTAINABLE GROWTH" — if:
  - All four levels positive and self-reinforcing
  - Not yet applicable for Argentina

## Report structure
Executive summary: 3 paragraphs
  Para 1: Verdict + one sentence justification
  Para 2: What the data shows (evidence for verdict)
  Para 3: Key risk that could change the verdict + timeline

Closing synthesis (end of report): 2 paragraphs
  Para 1: Reconnect all sections back to master variable
  Para 2: Forward-looking — what to watch in next 2 quarters
```

---

## LAYER 5: REPORT GENERATION

### Report structure (always in this order)
EXECUTIVE SUMMARY

Master verdict (from SKILL_master.md)
Key metrics snapshot table
Traffic light scorecard


GDP STRUCTURE AND GROWTH

Pie chart: current price composition full year
Growth contributions chart (C, G, I, NX contributions)
Production side: sector breakdown
Source: Cuadro 2, 11, 12 from INDEC


INVESTMENT DEEP DIVE (FBCF)

FBCF sub-component breakdown
Waterfall chart: contributions to FBCF growth
Dollar-draining vs dollar-neutral classification
Connection to reserves


LABOR MARKET AND WAGES

Real wage chart (YoY + MoM)
Formal employment trend
Productivity by sector
The master variable assessment


CONSUMPTION DRIVERS

C growth decomposition
Real wages vs credit expansion vs savings
Credit by destination (consumption/mortgage/business)
Sustainability assessment


INFLATION

Monthly CPI trend
Real rates
Connection to wage erosion


EXTERNAL DOLLAR SITUATION

Current account by component
Trade balance (goods + services)
Net reserves trend
Debt payment calendar
Energy trade balance


PRODUCTION AND ENERGY

EMAE by sector
Oil and gas production
Vaca Muerta trajectory
Dollar generation potential


CLOSING SYNTHESIS

Master variable reassessment
What to watch next 2 quarters
The bull and bear case in one paragraph each

### Traffic light scorecard (always include)
```python
SCORECARD_METRICS = {
    "Master Variable": {
        "metric": "real_wage_yoy",
        "green": "> 3%",
        "yellow": "0 to 3%", 
        "red": "< 0%"
    },
    "Investment": {
        "metric": "fbcf_yoy",
        "green": "> 10%",
        "yellow": "0 to 10%",
        "red": "< 0%"
    },
    "Inflation": {
        "metric": "cpi_mom",
        "green": "< 2%",
        "yellow": "2-4%",
        "red": "> 4%"
    },
    "Net Reserves": {
        "metric": "net_reserves_bn",
        "green": "> $5B",
        "yellow": "$0-5B",
        "red": "< $0"
    },
    "Current Account": {
        "metric": "current_account_quarterly_bn",
        "green": "> $1B surplus",
        "yellow": "-$1B to $1B",
        "red": "< -$1B deficit"
    },
    "Formal Employment": {
        "metric": "sipa_yoy",
        "green": "> 3%",
        "yellow": "0-3%",
        "red": "< 0%"
    },
    "Energy Production": {
        "metric": "oil_yoy",
        "green": "> 10%",
        "yellow": "0-10%",
        "red": "< 0%"
    },
    "Fiscal Balance": {
        "metric": "fiscal_surplus_pct_gdp",
        "green": "> 1.5%",
        "yellow": "0-1.5%",
        "red": "< 0%"
    }
}
```

---

## CODING STANDARDS

### When adding a new data series
1. Add fetch function to the appropriate fetch_*.py file
2. Add series ID to config.py
3. Add cleaning/deflation to process/*.py
4. Add to the relevant signals_*.py file
5. Update the relevant SKILL_*.md if interpretation changes
6. Test that main.py still runs end to end

### When adding a new analytical section
1. Decide which layer it belongs to
2. If it needs new data → Layer 1 first
3. If it needs new derived metrics → Layer 3
4. If it needs new interpretation rules → Layer 4 (skills)
5. Add to report structure in Layer 5
6. Always connect back to the master variable

### Error handling standard
```python
def fetch_with_fallback(primary_fn, fallback_fn, series_name):
    try:
        data = primary_fn()
        log(f"SUCCESS: {series_name} from primary source")
        return data
    except Exception as e:
        log(f"WARNING: {series_name} primary failed: {e}")
        try:
            data = fallback_fn()
            log(f"SUCCESS: {series_name} from fallback")
            return data
        except Exception as e2:
            log(f"CRITICAL: {series_name} both sources failed")
            return None  # Never crash — always continue with partial data
```

### Never
- Let the LLM compute percentages or do arithmetic
- Use constant price shares as the primary composition view
- Use simple subtraction instead of Fisher equation for deflation
- Hardcode dates — always use `datetime.now()` or latest available
- Crash on missing data — always degrade gracefully

### Always
- Cache raw data
- Validate that GDP components sum correctly (within 2%)
- Label whether a series is real or nominal
- Include the data source and series code in every output file
- Run a sum check on GDP composition before reporting shares
