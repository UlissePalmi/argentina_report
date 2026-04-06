# SKILL: Investment (FBCF)

## Purpose
Analyze fixed investment (Formacion Bruta de Capital Fijo) to assess whether Argentina is
building the productive capacity required for sustained real wage growth.
Investment is the primary **driver** — without rising capital per worker, productivity gains
cannot be sustained, and wage growth will remain credit-financed rather than productivity-backed.

## Data to read
- `data/signals/signals_investment.json` (primary)
- `data/gdp/gdp_fbcf.csv` (for sub-component detail if needed)

## Key metrics to focus on
1. `fbcf_yoy_proxy` — estimated total FBCF YoY (weighted average of sub-components)
2. `fbcf_constr_yoy` and `fbcf_maq_nac_yoy` — dollar-neutral components
3. `fbcf_maq_imp_yoy` and `fbcf_transport_yoy` — dollar-draining components
4. `dollar_draining_share_pct` — what % of FBCF requires FX
5. `consecutive_positive_quarters` — how many quarters of sustained investment growth

## Connection to master variable
Investment is the bridge between today's output and tomorrow's wages.
**Why it matters:**
- Construction growing → employment (direct, domestic labor) + infrastructure
- Domestic machinery growing → capital formation without FX drain
- Imported machinery growing → best signal of business confidence AND FX pressure
- Transport equipment growing → logistics capacity (Vaca Muerta, agro logistics)

**The dollar tension:** FBCF growth is good for wages but dangerous for reserves if the
growth is concentrated in imported components. Always classify the investment mix:
- Dollar-neutral recovery (construction + domestic machinery): supportive without FX stress
- Dollar-draining recovery (imported machinery + transport): positive for capacity, but
  each percentage point of growth requires reserve spend

## Interpretation rules

### Total FBCF thresholds
| Range | Assessment |
|---|---|
| > 15% YoY | Strong investment cycle — productive capacity expanding fast |
| 5–15% YoY | Moderate investment recovery — business confidence improving |
| 0–5% YoY | Stagnant — replacement-level investment, no real capacity expansion |
| < 0% YoY | Investment contraction — capital stock aging, future productivity at risk |
| < -10% YoY | Severe contraction — flag as warning, check if Argentina-wide recession signal |

### The dollar classification — always do this
For each quarter, compute:
- Dollar-neutral growth rate = weighted avg of (constr + maq_nac) using their shares
- Dollar-draining growth rate = weighted avg of (maq_imp + transport) using their shares
- Dominant driver: whichever group's contribution to FBCF is larger

If dollar-draining components > 40% of FBCF AND growing fast: flag reserve pressure.
If dollar-neutral components are driving recovery: flag as most favorable configuration.

### The mortgage-construction contradiction (always check)
Credit signals (`signals_credit.json`) may show real mortgage credit booming (+50-100% YoY)
while construction FBCF is contracting or flat. This is a structural contradiction:
- Mortgages booming + construction flat = credit financing transfers of existing homes, not new builds
- This drives price appreciation without adding housing supply
- Flag explicitly: "Mortgage boom is not a construction boom"

### Investment and the master variable timeline
Investment today → productivity gains in 2-4 quarters → real wage capacity in 4-8 quarters.
Even if investment is booming NOW, it will not show up in wages for several quarters.
Always note this transmission lag explicitly.

## Report section format
- Length: 2–3 paragraphs
- Lead with: total FBCF YoY growth and dominant driver
- Chart to reference: FBCF stacked bar (dollar-neutral vs dollar-draining shares)
- Always include: the dollar tension — which components are growing and FX implications
- Always include: mortgage vs construction cross-check if credit data available
- Connect to: External section (imported machinery growth = reserve demand)
- Connect to: Production section (is new investment appearing in output data yet?)

## Verdict options

**Productive investment cycle:**
FBCF > 10% YoY, driven by construction + domestic machinery, dollar-draining < 35% of mix.
*"Fixed investment grew [X]% YoY in Q[X], led by [dominant component]. The composition is
favorable — [dollar-neutral share]% of FBCF is dollar-neutral, limiting reserve pressure while
building domestic productive capacity. At this pace, productivity gains should begin appearing
in output data within 2-3 quarters."*

**Dollar-costly recovery:**
FBCF > 10% YoY but dominated by imported machinery + transport.
*"Fixed investment grew [X]% YoY in Q[X], but the composition raises reserve concerns.
[Dollar-draining share]% of FBCF consists of imported machinery and transport equipment —
each percentage point of investment growth has a direct FX cost. This is positive for
long-run capacity but creates near-term pressure on net reserves."*

**Investment stagnation:**
FBCF near zero or negative.
*"Fixed investment [grew/contracted] [X]% YoY in Q[X] — [the Nth consecutive quarter of
contraction/stagnation]. Without rising capital stock, productivity gains cannot accelerate,
and real wage growth will remain dependent on credit rather than output."*
