# SKILL: Production and Energy

## Purpose
Assess industrial production and energy sector output to determine:
1. Whether the productive base is expanding (feeding into future wage capacity)
2. Whether Vaca Muerta is on track to provide Argentina's permanent dollar solution
3. Whether the two-speed economy (commodity boom vs domestic weakness) is present

## Data to read
- `data/signals/signals_production.json` (primary)
- `data/production/production_monthly.csv` (for sub-sector detail)

## Key metrics to focus on
1. `ipi_yoy_latest` — industrial production index (manufacturing health)
2. `oil_yoy_latest` and `gas_yoy_latest` — energy sector trajectory
3. `vaca_muerta_signal` — qualitative assessment (strong/growing/marginal/stalling)
4. `ipi_trend_3m` — is momentum building or fading?
5. `isac_cement_yoy` — construction activity proxy (corroborates investment data)

## Connection to master variable
Production connects to the master variable through two channels:

**Channel 1: Productivity backing**
Industrial output rising faster than employment = productivity rising = real wages can
rise without inflation. This is the sustainable path. Check: IPI vs SIPA employment trends.

**Channel 2: Vaca Muerta dollar generation**
Oil and gas exports generate the dollars that allow Argentina to:
- Maintain the crawling peg (stable currency = no inflation spike)
- Build reserves (net reserves positive = no devaluation risk)
- Service external debt (no sovereign default risk)
Every barrel of Vaca Muerta oil produced is an enabler of wage stability.

## Interpretation rules

### Industrial production (IPI) thresholds
| Range | Assessment |
|---|---|
| > 5% YoY | Manufacturing expanding — broad-based productive capacity building |
| 0–5% YoY | Modest recovery — stabilization after recession |
| -3–0% YoY | Stagnant / slight contraction — domestic demand still soft |
| < -5% YoY | Manufacturing contraction — domestic economy weak |
| < -10% YoY | Severe contraction — flag explicitly |

### Oil/gas thresholds and Vaca Muerta signal
| Oil YoY | Assessment |
|---|---|
| > 15% | Strong ramp-up — structural story confirmed |
| 5–15% | Solid growth — trajectory intact |
| 0–5% | Modest growth — production plateauing |
| < 0% | Contraction — flag as concern for dollar generation |

**Vaca Muerta signal interpretation:**
- `strong`: Oil > 10% AND gas > 5% AND 3m trend confirming → permanent dollar solution on track
- `growing`: Oil positive, gas positive → normalizing path
- `marginal`: Oil barely positive → watch for plateau
- `stalling`: Oil near zero or negative → flag as risk to the structural energy narrative

### The two-speed economy test
Compare IPI vs oil/gas simultaneously:
- **Both positive:** Broad-based recovery — most favorable configuration
- **Oil/gas up, IPI down:** Commodity boom masking domestic weakness — flag explicitly as
  "commodity-driven growth that does not yet translate into domestic wage recovery"
- **IPI up, oil flat:** Domestic recovery without structural dollar generation — sustainable
  only if reserves are already comfortable
- **Both negative:** Broad contraction — flag as recession signal

### Sub-sector depth (if IPI sub-components available)
- `ipi_food_yoy`: agro-processing — follows harvest seasonality, not a cycle indicator
- `ipi_steel_yoy`: intermediate goods — leading indicator of construction and auto demand
- `ipi_auto_yoy`: consumer durables — direct demand signal, also export component

### Cement (ISAC) and investment coherence
`isac_cement_yoy` should move with construction FBCF. If:
- Cement growing + construction FBCF growing → confirmed investment pickup
- Cement growing + construction FBCF flat → leading indicator, FBCF will follow
- Cement falling + construction FBCF positive → suspect FBCF data, defer to cement

## Report section format
- Length: 2 paragraphs
- Para 1: Industrial production — what is driving it and is it broad-based?
- Para 2: Energy — Vaca Muerta trajectory and dollar generation potential
- Chart to reference: IPI monthly YoY + oil/gas production YoY
- Always include: the two-speed economy check
- Connect to: External section (oil production → energy trade surplus → reserve accumulation)
- Connect to: Investment section (cement corroborates or contradicts FBCF data)
- Connect to: Labor section (IPI trend should align with manufacturing employment)

## Verdict options

**Broad-based productive recovery:**
IPI positive + oil/gas growing.
*"Industrial output grew [X]% YoY in [month], with [sub-sector] leading the recovery.
Vaca Muerta production continues to accelerate: oil +[X]% and gas +[X]% YoY. The two-speed
economy concern is not present — both domestic manufacturing and the energy sector are expanding,
providing a more durable foundation for wages than commodity-only growth."*

**Commodity boom masking domestic weakness:**
Oil/gas up, IPI flat or negative.
*"Argentina's production picture remains bifurcated. Energy output is the headline story:
oil +[X]% and gas +[X]% YoY reflect Vaca Muerta's structural trajectory — a genuine dollar
generator. But industrial production [contracted/stagnated] at [X]% YoY, with [weakest sub-sector]
the most affected. Growth driven purely by commodity extraction does not by itself raise domestic
wages — it provides the reserve stability that enables wages to recover, but the domestic
transmission has not yet engaged."*

**Energy stalling + industrial weakness:**
Both metrics deteriorating.
*"Production signals are concerning on both fronts. Industrial output fell [X]% YoY — [Nth
consecutive month of contraction] — and Vaca Muerta momentum has slowed, with oil [flat/falling]
at [X]% YoY. Combined, these signals suggest the productive base is not expanding, which limits
the supply-side foundation for real wage recovery."*
