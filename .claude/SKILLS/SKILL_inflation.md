# SKILL: Inflation

## Purpose
Analyze the inflation trajectory and its direct impact on real purchasing power.
Inflation is the primary **enabler** in the master framework — falling inflation removes the
monthly erosion of nominal wages, allowing real wages to recover without requiring accelerating
nominal wage growth. Every basis point of monthly CPI is directly felt by households.

## Data to read
- `data/signals/signals_inflation.json` (primary)
- `data/inflation/indec_cpi.csv` (for the full monthly series if needed)

## Key metrics to focus on
1. `cpi_mom_latest` — the monthly rate; this is the number that directly erodes wages
2. `cpi_mom_trend_3m` vs `cpi_mom_trend_6m` — is disinflation structural or stalling?
3. `disinflation_confirmed` — boolean; only true if 3m avg < 6m avg
4. `consecutive_months_below_3pct` — how entrenched is the low-inflation regime?
5. `cpi_yoy_latest` — context; but always lead with MoM, not YoY

## Connection to master variable
Falling monthly CPI is the most direct enabler of real wage recovery.
Even flat nominal wages produce real wage growth if monthly inflation is 2% instead of 6%.
At 2%/month inflation, a worker earning 100 pesos sees 2 pesos eroded — manageable.
At 6%/month, 6 pesos is eroded every month — the same nominal wage produces real contraction.

**Always end the section by quantifying this link:**
If monthly CPI is X% and nominal wages grew Y% last month, compute the real MoM:
`real_mom ≈ (1 + Y/100) / (1 + X/100) - 1`

## Interpretation rules

### Monthly CPI thresholds
| Range | Assessment |
|---|---|
| < 1.5% MoM | Near price stability — developed-market territory |
| 1.5–2.5% MoM | Very low for Argentina — structural disinflation achieved |
| 2.5–4% MoM | Significant progress; real wages can recover if nominal growth > 4% |
| 4–7% MoM | Elevated; nominal wages must run at > 7% MoM to break even in real terms |
| > 7% MoM | Critical inflation; no real wage recovery possible at current pace |

### The disinflation test (apply before interpreting any monthly print)
A single low month is not disinflation. Three consecutive months below a threshold IS disinflation.
- **Confirmed:** `consecutive_months_below_3pct >= 3` AND `disinflation_confirmed = true`
- **Stalling:** MoM has been volatile around the threshold — do not call structural change
- **Re-accelerating:** `cpi_mom_trend_3m > cpi_mom_trend_6m` — flag as risk even if level is low

### Base effect warning
Argentina's monthly CPI was 25% in December 2023. YoY comparisons from late 2024 onward
will show dramatic declines mechanically. **Never use YoY as the primary metric.**
Always lead with MoM. Only use YoY for historical context.

### Real rate interpretation
If BCRA benchmark rate is 20% annualized = ~1.5% monthly, and CPI is 2.5% monthly:
Real rate = approximately -1% monthly → negative real rates → accommodative monetary policy.
This affects credit demand (stimulative) and currency stability (dollarization risk if real rates
stay negative for extended periods). Note this qualitatively if rate data is available.

## Report section format
- Length: 2 paragraphs
- Lead with: MoM CPI latest print and whether disinflation is confirmed
- Chart to reference: monthly CPI series (12-month bar or line chart)
- Always include: the 3m vs 6m comparison to test structural vs noise
- Connect to: Wages section (how much inflation is eating each month)
- Connect to: External section (crawling peg depreciation vs inflation = real FX appreciation)

## Verdict options

**Structural disinflation achieved:**
Monthly CPI below 3% for 3+ consecutive months, 3m avg below 6m avg.
*"Inflation has structurally broken lower. Monthly CPI of [X]% represents a [Y]pp decline
from the [peak] — real wages can now recover even at moderate nominal growth rates."*

**Disinflation in progress:**
Monthly CPI declining but not yet sustained below 3%.
*"Inflation is trending lower but structural disinflation is not yet confirmed.
The 3m average of [X]% is [above/below] the 6m average of [Y]% — watch for the next 2 months."*

**Inflation stalling:**
Monthly CPI flat or re-accelerating above 4%.
*"Disinflation has stalled at [X]% MoM — real wages cannot recover until monthly inflation
breaks sustainably below [threshold]. The key risk is [specific driver if identifiable]."*
