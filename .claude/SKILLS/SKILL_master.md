# SKILL: Master Synthesis

## Purpose
Synthesize all domain analyses into a single verdict on whether Argentina is building
conditions for sustainable real wage growth. This is the opening and closing section of the
report — it frames the analytical question, announces the verdict, and closes with the
forward-looking risk assessment.

**The central question every report must answer:**
*"Is Argentina building the conditions for sustainable real wage growth,
or is it just going through another temporary recovery that will reverse?"*

## Data to read
- `data/signals/signals_master.json` (primary — contains all pre-aggregated signals)
- All domain signals in `data/signals/` if more detail is needed

## The four questions (answer all four explicitly)

### 1. MASTER VARIABLE: Are real wages positive and trending up?
From `signals_master.json`:
- `master_variable.value` — current real wage YoY
- `master_variable.trend_3m` — momentum
- `master_variable.consecutive_positive_months` — sustainability test
- `master_variable.backed_by_productivity` — is it real or credit-financed?

**The verdict hangs on this number.** If real wages are negative, no matter how good the
enablers are, Argentina has not yet crossed the threshold. If positive, test whether
it is wage-led or credit-led.

### 2. DRIVERS: Is productive capacity being built?
- `drivers.investment_fbcf_yoy` — is capital stock growing?
- `drivers.formal_employment_yoy` — is the formal labor base expanding?
- `drivers.productivity_trend` — is output per worker rising?
- `drivers.credit_discipline` — is credit supplementing or substituting for wages?

**Key judgment:** If investment is growing but wages are still negative, flag this as
"conditions forming — not yet arrived." If investment is falling and wages are positive,
flag this as "consumption-led recovery without supply-side backing — watch sustainability."

### 3. ENABLERS: Is the macro environment stable enough?
- `enablers.inflation_mom_latest` — the monthly erosion rate
- `enablers.disinflation_confirmed` — structural or noise?
- `enablers.gross_reserves_bn` — gross buffer (net is lower — always caveat)
- `enablers.reserves_trend` — accumulating or depleting?
- `enablers.current_account_bn` — quarterly flow position

**Enablers are necessary but not sufficient.** Low inflation and positive reserves create
the environment for wage recovery, but they do not themselves produce it. The mistake is
to confuse stabilization with growth.

### 4. ACCELERATORS: Is the structural transformation on track?
- `accelerators.oil_yoy` — Vaca Muerta volume growth
- `accelerators.vaca_muerta_signal` — qualitative signal
- `accelerators.gas_yoy` — gas production (LNG export potential)

**Vaca Muerta is Argentina's asymmetric bet.** If Vaca Muerta delivers, Argentina has a
permanent dollar solution that removes the external constraint permanently. If it stalls,
the current recovery faces the same external ceiling as every prior cycle.

## Verdict framework

Read `signals_master.json.verdict` and justify it with data. Do not override the computed
verdict without strong reason — but always explain it in plain language.

| Verdict | What it means | Key conditions |
|---|---|---|
| `crisis_risk` | Imminent macro crisis | Wages negative + investment falling + reserves depleting |
| `fragile_recovery` | Recovery real but unsustainable | Wages positive but credit-driven + investment weak |
| `structural_improvement_underway_unconfirmed` | Conditions forming, wages not yet positive | Enablers fixed, drivers building, master variable negative |
| `recovery_confirmed_watch_sustainability` | Recovery confirmed, watch what sustains it | Wages positive 3+ quarters, backed by productivity |
| `sustainable_growth` | Self-reinforcing cycle | All four levels positive |

**Current expected verdict (Q4 2025):** `structural_improvement_underway_unconfirmed`
Enablers (inflation, fiscal, reserves) have improved significantly. Drivers (investment,
employment) are building. But the master variable (real wages) has only recently turned positive
and is not yet confirmed as sustained. This is the most likely verdict unless data shows otherwise.

## Scorecard table
Always include the scorecard from `signals_master.json.scorecard`. Present as a table:

| Metric | Value | Signal |
|---|---|---|
| Real wages YoY | [X]% | green/yellow/red |
| FBCF YoY | [X]% | ... |
| Monthly CPI | [X]% | ... |
| Gross Reserves | $[X]B | ... |
| Current Account | $[X]B | ... |
| Formal Employment | [X]% | ... |
| Oil Production | [X]% | ... |

## Report structure

### Opening (Executive Summary — 3 paragraphs)

**Para 1: Verdict + one sentence justification**
State the verdict label, then the single most important fact that justifies it.
Do not pad. Do not hedge. Give a directional call.

Example: *"STRUCTURAL IMPROVEMENT UNDERWAY — UNCONFIRMED. Argentina has fixed the macro
environment but has not yet converted stability into sustained real wage growth."*

**Para 2: Evidence (what the data shows)**
Walk through the four levels: master variable, drivers, enablers, accelerators.
One sentence per level. Use specific numbers from the scorecard.

**Para 3: Key risk that could change the verdict + timeline**
Name ONE specific risk that could push the verdict UP or DOWN, and name a timeframe.
Do not list five risks — pick the most important one.

Example: *"The verdict will upgrade to RECOVERY CONFIRMED if real wages remain positive for
two more quarters (by Q2 2026) and consumer credit growth decelerates below 30% real YoY.
The risk that could downgrade it is a stall in the crawling peg adjustment triggering
import compression before investment has replaced import demand."*

### Closing Synthesis (end of report — 2 paragraphs)

**Para 1: Reconnect all sections to the master variable**
One sentence per section reviewed, reconnecting the evidence to the central question.
This is not a summary — it is a synthesis. The thread should be: Inflation fell → real wages
could recover → but credit is supplementing not replacing wages → investment is building capacity
→ if Vaca Muerta delivers dollars → the enabling constraints are permanently lifted.

**Para 2: Forward-looking — what to watch in next 2 quarters**
Name exactly 3 data points to watch. Why each one matters. What change would signal a
verdict upgrade vs a downgrade.

## Tone guidelines
- Be analytical, not cheerleading and not alarmist
- Always qualify: "the data shows X, which suggests Y, conditional on Z"
- Never say "Argentina has turned the corner" without the specific metrics that define the corner
- Never say "crisis is inevitable" — Argentina has surprised before
- The honest answer in Q4 2025 is: conditions are better than they have been in years,
  but the proof is still ahead of us
