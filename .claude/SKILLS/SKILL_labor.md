# SKILL: Labor Market and Wages

## Purpose
Assess formal employment growth and productivity trends to determine whether real wage gains
(the master variable) are backed by genuine productive capacity, or are fragile transfers
at risk of reversal. Labor is the most direct connection to the master variable.

## Data to read
- `data/signals/signals_wages.json` (primary — real wage metrics)
- `data/signals/signals_labor.json` (primary — employment + productivity)
- `data/productivity/employment.csv` (sector detail if needed)
- `data/productivity/productivity.csv` (ULC detail if needed)

## Key metrics to focus on
1. `real_wage_yoy_latest` (from wages signal) — THE master variable
2. `real_wage_trend_3m` — is the recovery accelerating or fading?
3. `consecutive_positive_months` — sustainability test (9+ months = 3 quarters = confirmed)
4. `sipa_yoy_latest` — formal employment growth (productive sector expansion)
5. `productivity_industry_yoy` — output per worker in manufacturing
6. `ulc_industry_yoy` — unit labor cost trend (wage growth vs productivity)

## Connection to master variable
This section IS the master variable assessment.
The central question: **Are real wages positive because the economy is more productive,
or because credit is allowing households to smooth consumption temporarily?**

The test:
- Real wages positive + productivity positive + ULC moderate → **sustainable**
- Real wages positive + productivity negative + credit booming → **fragile, credit-driven**
- Real wages negative + employment contracting → **erosion phase, no recovery yet**
- Real wages negative + employment growing → **recovery in volume but not yet in pay**

## Interpretation rules

### Real wage thresholds
| Range | Assessment |
|---|---|
| > 5% YoY | Strong real recovery — purchasing power clearly improving |
| 0–5% YoY | Modest recovery — better than zero but fragile without further drivers |
| -5–0% YoY | Slight contraction — households losing purchasing power slowly |
| < -5% YoY | Severe erosion — domestic consumption under pressure |

### The 3-quarter rule
Real wages positive for 1 month: noise.
Real wages positive for 3 consecutive months: trend.
Real wages positive for 9 consecutive months (3 quarters): confirmed recovery.
**Always state explicitly how many consecutive positive months have been recorded.**

### Productivity backing test
Use `ulc_industry_yoy` as the key diagnostic:
- ULC falling (negative) → productivity growing faster than wages → sustainable
- ULC rising 0–10% → wages slightly ahead of productivity → watch
- ULC rising > 10% → wages materially outpacing productivity → unsustainable, inflation pressure builds

### Formal employment (SIPA) interpretation
SIPA = registered private employment (formal sector). Rising SIPA means:
- More workers in tax-paying, benefit-receiving jobs (structural improvement)
- Broader wage bill (more total income in the formal economy)
- Stronger foundation for consumption growth (formal workers spend more reliably than informal)

SIPA falling is more alarming than informal employment falling because formal jobs are harder
to create than to destroy — each lost formal job takes 3–6 months to recreate.

### The two-speed warning
If service-sector employment grows while manufacturing employment contracts:
This is jobs recovery led by lower-productivity services, not manufacturing.
Real wages may recover in aggregate but be weaker at the median.
Flag explicitly: "Employment recovery is service-led — productivity implications are weaker
than headline formal employment growth suggests."

### Base effect rule
SIPA data from 2024 compares against deep recession of 2023. Any % changes in 2024–2025
are coming off a low base. Check whether the LEVEL has recovered to pre-crisis (2022) levels,
not just whether the YoY change is positive.

## Report section format
- Length: 2–3 paragraphs
- Para 1: Real wages — latest, trend, consecutive positive months, is it sustainable?
- Para 2: Formal employment — is the productive labor base expanding?
- Para 3 (if data available): Productivity and ULC — is wage growth productivity-backed?
- Chart to reference: real wage YoY line chart + employment YoY
- Connect to: Consumption section (wages are the source of sustainable consumption)
- Connect to: Production section (is employment recovery matching output recovery?)
- Connect to: Credit section (is wage recovery genuine or credit-supplemented?)

## Verdict options

**Wage-led recovery (sustainable):**
Real wages > 0, consecutive positive months >= 6, productivity neutral to positive.
*"Real wages recovered [X]% YoY in [month], the [Nth] consecutive month of positive real
wage growth. Formal employment grew [X]% YoY — the productive labor base is expanding.
Productivity trends suggest these gains are not exclusively redistribution: industrial output
per worker [rose/held steady], and unit labor costs [fell/rose modestly]. This is the most
favorable configuration for the master variable."*

**Recovery without productivity (watch):**
Real wages positive but productivity falling or credit spread high.
*"Real wages grew [X]% YoY but this recovery is partially credit-supplemented. Consumer credit
is growing [spread]pp faster than wages — households are borrowing alongside earning. Formal
employment is [expanding/flat]. The key question is whether productivity catches up before
the credit cycle turns."*

**Pre-recovery phase:**
Real wages negative but employment growing, inflation falling.
*"Real wages contracted [X]% YoY — purchasing power is still being eroded. However, formal
employment grew [X]%, inflation has fallen to [X]%/month, and the 3m trend in real wages
is [improving/stable]. The conditions for real wage recovery are forming but have not yet
appeared in the data."*
