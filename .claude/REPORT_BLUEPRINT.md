# Argentina Weekly Macro Monitor — Report Blueprint

*Design specification for an internal hedge-fund macro product. This document defines the report's architecture, every section's purpose, the exact metrics and charts, the analytical thresholds, and the signal logic. It is the blueprint, not the report.*

---

## 0. Design Philosophy (read this first)

This report exists to answer **one question every week**: *Is the disinflation-cum-stabilization regime gaining or losing durability, and what does that mean for the price of ARS bonds, the peso, and Argentine risk?*

Everything in the report is subordinate to that question. Argentina is not a "growth" story for the PM — it is a **regime-credibility** story. The asset prices (Globals, Bonares, BOPREAL, peso curve, the official-vs-parallel gap, the Merval in CCL terms) are all derivatives of a single latent variable: *the market's probability that the stabilization holds without a disorderly devaluation or a financing accident.* The report's job is to track that probability with harder data than the market is using.

Three structural facts frame the entire document and should be restated on the cover page each week:

1. **The binding constraint is dollars, not pesos.** The fiscal anchor (déficit cero) is the government's great achievement and is largely *solved* as a flow problem; the unsolved problem is the **stock and flow of reserves**. A government can run a primary surplus and still hit a balance-of-payments wall. This is why Section 2 (Reserves) is the spine of the report, not Section 5 (Fiscal).
2. **The regime is a managed FX framework under an IMF EFF with hard NIR targets.** The single most market-relevant number in Argentina is **Net International Reserves vs the IMF target path.** A miss forces a waiver request; a waiver request reprices the entire curve. Track it like an earnings number.
3. **There is a structural dollar engine being built underneath the cyclical fragility** — energy (Vaca Muerta) and mining/agriculture. The bull case is that the structural trade surplus arrives before the cyclical financing wall. The bear case is the reverse. The report is, at its core, a **race between these two clocks.** Every section should be readable as evidence for which clock is winning.

**Cadence & diff discipline.** This is a *weekly* product. The reader has seen last week's edition. Therefore the report is organized around **change**, not levels. Every section carries a `WHAT CHANGED THIS WEEK` box at the top. Levels are reference; deltas are the product.

**Operating-assumption note for the analyst.** This blueprint assumes the post-April-2025 regime architecture: a crawling **band** (not a pure crawl), partial cepo lift, blend dollar eliminated, an active EFF with NIR performance criteria, and quasi-fiscal liabilities migrated from BCRA to Treasury (LEFI). Where the live regime differs at publication date, the analyst adapts the FX and reserves sections first — those are the regime-sensitive ones.

---

## Table of Contents

**Front Matter**
- Cover: One-line verdict + macro scorecard + the three clocks (NIR vs target / disinflation / activity)
- Event calendar (next 8 weeks)

**Part I — The Spine (External Solvency)**
1. Executive Summary & Macro Scorecard
2. **BCRA Reserves** *(longest section — the spine)*
3. Exchange Rate & FX Regime
4. External Accounts & the Dollar-Flow Calendar

**Part II — The Anchors (Domestic Stabilization)**
5. Inflation
6. Fiscal Balance & the Quasi-Fiscal
7. Debt & the Financial Program
8. Monetary & Peso Curve *(added — see note)*

**Part III — The Real Economy (Sustainability & Political Runway)**
9. Real Activity — GDP & EMAE
10. Production & Energy *(the structural-dollar engine)*
11. Labor Market & Real Wages
12. Consumption & Credit

**Part IV — The Meta-Layer**
13. Regime & Political Risk
14. Asset-Price Dashboard & Positioning *(added — see note)*
15. Risk Register & Trade Expression

*Two sections were added to the required list: **§8 Monetary & Peso Curve** (the peso-debt rollover and base-money/remonetization dynamics are too central to fold into Fiscal or Debt) and **§14 Asset-Price Dashboard** (a buy-side report must close the loop from macro to mark-to-market and explicit trade expression — otherwise it is a sell-side note). The "Consumption & Credit" and "Production" requested sections are retained but reordered into a coherent Part III.*

---

# PART I — THE SPINE

---

## 1. Executive Summary & Macro Scorecard

**Purpose & analytical hook.** Give the PM the entire thesis in 90 seconds and a single committed verdict. This page must be readable standing up. The hook: *"Where is Argentina in the adjustment cycle, is it moving forward or backward this week, and is the current asset-price level cheap or rich to that reality?"*

**Key metrics (the scorecard).** A traffic-light table, one row per domain, four columns: `Level` / `Trend (4wk)` / `Signal (G/A/R)` / `Δ vs last week`. Domains and their single summary metric:

| Domain | Headline metric | Why this one |
|---|---|---|
| Reserves | NIR vs IMF target ($bn gap) | The binding constraint |
| FX regime | Spot position within band (%) + brecha (%) | Devaluation pressure gauge |
| Inflation | Core MoM (%) | The anchor markets price |
| Fiscal | 12m rolling primary balance (% GDP) | Durability of the anchor |
| Debt/financing | Months of FX coverage for hard-cy maturities | Accident probability |
| Peso curve | Real ex-ante rate (TEM − expected infl) | Carry sustainability |
| Activity | EMAE 3m/3m annualized | Political runway |
| Real wages | Registered real wage YoY | Social-tolerance gauge |
| Politics | Govt legislative bloc + approval Δ | Reform reversibility |

**Below the scorecard:** one paragraph per domain (≤4 sentences), each ending in a directional clause. Then a single **Overall Verdict**, chosen from a fixed ladder so week-to-week moves are legible:

> `BOP CRISIS RISK` → `FRAGILE / TARGET-MISS WATCH` → `STABILIZING, UNCONFIRMED` → `STABILIZATION HOLDING, WATCH SUSTAINABILITY` → `STRUCTURAL TURN CONFIRMED`

**Chart specifications.** One chart only: the **"Two Clocks" chart** — dual-axis, last 18 months. Left axis: NIR ($bn) with the IMF target path overlaid as a stepped line (shade the gap red/green). Right axis: core inflation MoM (%). Annotate regime breaks (band introduction, cepo steps, IMF reviews, elections). This single chart *is* the thesis: dollars on one axis, the price anchor on the other.

**Narrative framework.** The verdict moves up the ladder only when **both** the external clock (NIR meeting target) and the nominal anchor (core inflation falling or stable-low) confirm together. Activity and politics can *cap* the verdict (a strong economy with collapsing reserves is still `FRAGILE`) but cannot *lift* it past what reserves allow. State explicitly each week which factor is the binding cap on the verdict.

**Bull/bear flags.** Bull: scorecard shows ≥6 green and zero red, with NIR green. Bear: NIR red is an automatic ceiling of `FRAGILE` regardless of everything else — write this rule in stone so the report never gets seduced by a good growth print while reserves bleed.

**Cross-section linkages.** This section is purely a roll-up; its discipline is that every cell must be traceable to a downstream section, and the verdict must be reconcilable with §14's positioning (if the verdict is bullish but the book is short, say why).

**Bottom line.** Commit to one ladder rung and one sentence: *"We are at [rung]; the binding constraint this week is [X]; the trade that expresses this is [Y]."*

---

## 2. BCRA Reserves — *The Spine*

**Purpose & analytical hook.** This is the section the whole report is built around. The hook: *"Does the central bank have, or can it credibly acquire, enough dollars to defend the regime through the next seasonal trough and the next debt-payment cluster — and is it on track for the IMF's NIR target?"* Every other section is ultimately an input to this one. If the PM reads only one section, it is this one.

### 2A. The reserve stack — define every layer precisely

The report must publish a **waterfall** from Gross to "Net-Net" every week, because the headline gross number is the most misleading figure in Argentine macro and the spread between the layers *is* the analysis. Define and quantify each layer:

**Gross International Reserves (GIR / Reservas Brutas)** — BCRA's total reported stock. Components, each tracked as its own line:
- **Liquid FX** (USD and convertible currencies)
- **Gold** — and critically, *where it is held* (a portion was reportedly moved offshore to be usable as collateral; flag any custody change as a signal that BCRA is preparing to pledge it)
- **SDR holdings** at the IMF
- **The PBOC yuan swap, activated portion** — counted in gross but not usable as free reserves; this is the single biggest reason gross overstates strength
- **Banks' FX reserve requirements (encajes)** — dollar deposits of commercial banks parked at BCRA. *This is depositors' money, not the BCRA's.* It inflates gross and can vanish in a deposit run.
- **BIS / repo lines and other short-term FX liabilities**

**Net International Reserves (NIR / Reservas Netas)** = Gross − (yuan swap activated − or the analyst's chosen treatment) − bank FX encajes − BIS repos − other ST FX liabilities. **Publish the exact formula used and never change it without flagging.** Note the live methodological dispute: some desks subtract the *entire* swap, others only the *activated* tranche; the IMF's NIR definition is its own animal (see 2D). Show **all three** (analyst-net, swap-excluded-net, IMF-net) in a small table so the PM can map any headline they hear to your number.

**"Net-Net" / Reservas Líquidas Netas** = NIR − SDRs that are encumbered − hard-currency sovereign/BCRA payments due within the next ~90 days. This is the genuinely deployable war chest and is frequently *negative*. This number is the true "how many bullets does the central bank have" gauge.

### 2B. Reserve-change decomposition — the weekly money shot

A stacked bar / bridge chart decomposing the **week-over-week and month-over-month ΔNIR** into sources. This is the most analytically valuable single object in the report:

- **Trade settlement flows** (MULC net of exporter liquidation vs importer demand)
- **BCRA spot intervention** (purchases at the band floor / sales at the ceiling — under the EFF, BCRA pledges *not* to intervene inside the band, so any inside-band sale is a regime-stress tell)
- **Treasury dollar purchases** (post-band, accumulation migrated partly to the Tesoro buying blocks of FX from its peso surplus — track this separately; it is the new accumulation channel)
- **IMF / multilateral disbursements** (IDB, World Bank, CAF)
- **PBOC swap activations / cancellations**
- **REPO with international banks** (BCRA has used bank repos to pad gross — flag new repos as *borrowed*, not *earned*, reserves)
- **Debt service paid in FX** (sovereign coupons/amortizations, BOPREAL)
- **Other** (valuation: gold price, EUR/USD, SDR revaluation — strip this out so the PM sees flow vs price)

The rule: **distinguish reserves that were *earned* (trade surplus, genuine FDI) from reserves that were *borrowed* (repos, swap, multilateral disbursements).** A week of +$1bn gross that is all repo is bearish dressed as bullish.

### 2C. Adequacy ratios

Track four, each with its threshold and trend:
- **Import cover** (GIR and NIR ÷ monthly goods imports) — target ≥3 months on gross; NIR is usually alarmingly low here
- **NIR as % of M2** (and of M3) — the dollarization-vulnerability ratio; how much peso could chase how few dollars
- **NIR ÷ short-term external debt + 12m amortizations** — the Guidotti-Greenspan rule; <1 is a flashing light
- **IMF ARA metric** (% of the Fund's reserve-adequacy composite) — Argentina runs far below the 100–150% adequate range; track the trajectory, not the level

### 2D. The IMF NIR target — *the earnings number*

A dedicated sub-panel. The EFF carries **quarterly NIR floors as performance criteria.** Track:
- The **target path** (each test date and required NIR level)
- **Current NIR vs the nearest test** ($bn ahead/behind)
- **Implied required weekly accumulation** to hit the next test from today
- **Run-rate vs required-rate gap** — if BCRA must buy $X/week and is buying $Y<X, quantify the shortfall and the implied **waiver probability**

A target miss → waiver request → review delay → disbursement delay → curve repricing. This causal chain should be drawn explicitly. **This panel is the most price-relevant object in the entire report.**

### 2E. Seasonality & the crawling-peg/band arithmetic

- **Seasonal map:** April–July is the soy/corn settlement window (peak dollar inflow); the Q4–Q1 stretch (Dec–March) is the seasonal trough (energy import bills historically, tourism dollar outflow, importer demand, dividend season). Overlay the typical seasonal NIR pattern so a "bad" week in the strong season reads as worse than the same number in the weak season.
- **Regime arithmetic:** under a pure crawl, real appreciation ≈ (inflation − crawl rate); under the band, the live questions are (i) where spot sits in the band, (ii) the band's slope, (iii) whether BCRA is being forced to the floor (accumulation, bullish) or the ceiling (defense, bearish). Compute the **implied NIR trajectory** by combining the dollar-flow calendar (§4) with the current accumulation run-rate, and state the **reserve level at which the band's floor commitment becomes incredible.**

**Chart specifications (this section gets the most real estate — ~6 charts):**
1. **The reserve waterfall** (Gross → NIR → Net-Net), this week vs 4 weeks ago vs 1 year ago — bar-of-bars.
2. **NIR vs IMF target path**, 18m, stepped target, shaded gap. *(Hero chart, repeated from cover.)*
3. **Weekly ΔNIR decomposition bridge**, trailing 13 weeks, earned vs borrowed color-coded.
4. **Gross vs Net vs Net-Net time series**, 24m — the diverging spread is the story.
5. **Seasonal NIR pattern** — current year vs prior 3-year average, indexed.
6. **Adequacy ratio panel** — small multiples, four ratios with threshold lines.

**Narrative framework.** Three regimes of interpretation: (a) **Accumulation** — earned reserves rising, beating IMF path, Net-Net climbing toward positive → the bull regime; (b) **Borrowed stability** — gross flat/up but composition deteriorating (repos, swap, encajes rising as a share) → false comfort, fade rallies; (c) **Bleed** — NIR falling against target in the strong season → pre-crisis, the floor commitment is on the clock. State which regime is live every week.

**Bull/bear flags.**
- 🟢 NIR ahead of IMF target *and* the beat is earned (trade/Treasury purchases, not repo); Net-Net turns positive; gold custody unchanged; no inside-band selling.
- 🔴 NIR behind target with <8 weeks to a test date and run-rate below required; inside-band FX *sales*; new large repos or swap activation to flatter gross; gold pledged/moved; encajes rising as a share of gross (deposit money propping the headline).

**Cross-section linkages.** Reserves are the integral of §4 (external flows) and §7 (debt payments); they are *constrained* by §3 (the regime BCRA is defending); they are *fed structurally* by §10 (energy/mining dollars) and *drained cyclically* by §9/§12 (activity recovery pulls in imports — the cruel irony that growth worsens the BoP). When activity (§9) accelerates, pre-warn the reserve drain here.

**Bottom line.** Commit: *"NIR is [ahead/behind] the IMF path by $X and the run-rate [does/does not] close the gap before [test date]; reserves are in the [accumulation/borrowed/bleed] regime. We are [buyers/sellers] of the curve into this, invalidated if [trigger]."*

---

## 3. Exchange Rate & FX Regime

**Purpose & analytical hook.** *"Is the FX framework credible at current reserve levels, and is the peso cheap or expensive enough to matter for the trade?"* The reserves section says how many bullets; this section says whether the gun is pointed at a credible target.

**Key metrics.**
- **The dollar complex:** official (A3500), and the parallels — **CCL** (contado con liqui), **MEP/bolsa**, **blue** (informal). Track each level and, more importantly, each **gap (brecha) to official** in %.
- **Position within the band** (% of distance from floor to ceiling) and **band slope** (% per month of both edges).
- **Real effective exchange rate (REER / TCRM)** — BCRA's multilateral index; the single best "is the peso expensive" gauge. Track vs the post-2001 historical distribution (percentile).
- **Real bilateral vs USD and vs BRL** — Brazil is the relevant competitiveness anchor; the ARS/BRL cross drives industrial competitiveness and is a recurring devaluation trigger.
- **ROFEX / A3 futures curve** — implied monthly devaluation by tenor; the market's priced path of the band.
- **Forward-implied vs band-implied spread** — if futures price devaluation faster than the band slope, the market disbelieves the band. This spread is the **market's devaluation-probability gauge.**
- **Blue-chip swap volumes / CCL turnover** — liquidity and capital-flight pressure.

**Chart specifications.**
1. **The dollar fan** — official + CCL + MEP + blue, 18m, with band edges drawn; shade the brecha.
2. **REER vs history** — TCRM index 24m with the long-run mean and ±1σ bands; annotate "competitiveness danger zone."
3. **ROFEX implied-devaluation curve** vs the band-slope path — this week vs 4 weeks ago.
4. **Spot-within-band gauge** — a simple position bar, floor to ceiling.

**Narrative framework.** The credibility test is the **brecha** and the **futures-vs-band spread.** A near-zero brecha with futures tracking the band slope = credibility intact. A widening brecha or futures pricing devaluation above the band = the market is front-running a break. The REER tells you the *fundamental* pressure (an overvalued peso accumulates devaluation pressure even if the brecha is calm); the brecha/futures tell you the *acute* pressure. Both matter; distinguish them every week. Key turning point: spot pinned to the **ceiling** with BCRA selling = the regime is being tested *now*; spot at the **floor** with BCRA buying = the bullish accumulation regime.

**Bull/bear flags.**
- 🟢 Brecha <10% and stable; futures at/below band slope; spot drifting toward the floor; REER stabilizing off the strong end.
- 🔴 REER in the "cheap dollar / expensive peso" tail (rich vs history); brecha widening; futures pricing devaluation > band slope; spot at ceiling with intervention. Argentina's recurring failure mode is *defending an overvalued peso until reserves run out* — this section's job is to catch that movie early.

**Cross-section linkages.** Overvaluation here (rich REER) is the leading indicator of the import surge in §4 and the reserve bleed in §2. The brecha is the cleanest real-time read on §13 (political/confidence) stress. Inflation (§5) vs the band slope determines REER drift — wire §3 and §5 together explicitly.

**Bottom line.** *"The peso is [cheap/fair/rich] at the [N]th percentile REER; the market [does/does not] believe the band (futures-band spread = X); acute pressure is [low/building]. Devaluation-risk read: [low/medium/high]."*

---

## 4. External Accounts & the Dollar-Flow Calendar

**Purpose & analytical hook.** *"Over the next one to two quarters, do the dollars coming in exceed the dollars going out — and by enough to feed the reserve target in §2?"* This section turns the balance of payments into a **forward cash-flow calendar**, not a backward-looking accounting statement.

**Key metrics.**
- **Trade balance (goods)** — monthly, with **export and import volumes vs prices** decomposed (a surplus driven by collapsing imports = recession, bearish; driven by rising exports = structural, bullish). INDEC ICA monthly.
- **Energy trade balance** — broken out separately (the Vaca Muerta structural story; see §10). The swing from chronic energy *deficit* to *surplus* is the single biggest structural BoP improvement.
- **Services balance** — tourism is a chronic dollar *drain* (Argentines traveling out); track the tourism deficit, sensitive to an overvalued peso (links to §3).
- **Current account** — full, with primary income (profit/dividend remittances, interest) and the trade core.
- **Financial account** — FDI, portfolio flows, the **RIGI** (large-investment incentive regime) pipeline of committed projects.
- **The harvest/settlement calendar** — expected agro-dollar liquidation by month for the next quarter, given crop estimates (§10) and farmer-holding behavior (farmers withhold grain as a peso-devaluation hedge; track the "silobolsa" stock — unsold grain is a *latent* dollar supply that price/policy can unlock).

**Chart specifications.**
1. **Trade balance with volume/price decomposition** — stacked, 24m.
2. **Energy balance** standalone — the structural-turn chart, 36m, to show the trend break.
3. **Dollar-flow calendar (forward)** — a bar chart of *projected* monthly net FX flows for the next 6 months (agro liquidation + energy + tourism + debt service), the report's most forward-looking object.
4. **Current account components** — quarterly stacked.

**Narrative framework.** Decompose every trade surplus into *quality* (export-led structural vs import-compression cyclical). The forward calendar is the bridge to §2: it tells the PM whether the reserve target is *seasonally reachable* or requires policy action (a devaluation to unlock the silobolsa, new external financing, etc.). The agro-withholding dynamic is a key reflexive loop: weak peso credibility → farmers hoard → dollar supply falls → reserves weaken → peso credibility weakens further.

**Bull/bear flags.**
- 🟢 Export-volume-led trade surplus; energy surplus widening; RIGI FDI pipeline converting to actual inflows; silobolsa liquidating into the strong season.
- 🔴 Surplus that is purely import-compression (turns to deficit the moment activity recovers); tourism deficit ballooning on an overvalued peso; farmers hoarding into a weak-peso narrative; primary-income drain rising as profit remittances are liberalized.

**Cross-section linkages.** This is the *flow* that integrates into the *stock* in §2. Import behavior is a function of §3 (FX level) and §9 (activity). Energy exports are sourced from §10. Profit-remittance liberalization is a §13 policy variable that drains the current account.

**Bottom line.** *"The forward dollar calendar shows a net [surplus/deficit] of ~$Xbn over the next quarter; this [is/is not] sufficient to meet the §2 reserve path without new financing. The trade surplus is [structural/cyclical]."*

---

# PART II — THE ANCHORS

---

## 5. Inflation

**Purpose & analytical hook.** *"Is the nominal anchor still working, and is the disinflation path fast enough to keep the REER from overheating before reserves are rebuilt?"* Disinflation is the government's political product and the bondholder's coupon-protection story; its *speed relative to the crawl* is the REER time bomb.

**Key metrics.**
- **CPI MoM and YoY** — headline, **core (núcleo)**, regulated (regulados), and seasonal (estacionales). INDEC, monthly (~mid-month for prior month); supplement with CABA CPI (earlier release) and high-frequency private trackers (PriceStats-style / consultancy weeklies) for a real-time lead.
- **Core MoM** is the anchor metric — it strips the noise and the policy-driven tariff catch-ups.
- **Annualized 3m core** — the cleanest "current run-rate" read.
- **Inflation expectations** — BCRA's **REM** (market expectations survey), monthly: next-month, year-end, 12m-ahead.
- **Breakeven-style read** — CER (inflation-linked) vs fixed (LECAP) peso curve implied breakeven inflation (links to §8).
- **Regulated-price pipeline** — pending tariff (utility/transport) adjustments are the *known future inflation*; track the announced schedule.

**Chart specifications.**
1. **CPI MoM** — headline vs core, 24m, with the implicit "disinflation glidepath" target overlaid.
2. **Core MoM vs crawl/band slope** — the REER-pressure chart; when core > band slope, the peso is appreciating in real terms (wire to §3).
3. **Category heatmap** — MoM by division, last 6 months, to see what's decelerating vs sticky (services/wages stickiness is the last-mile problem).
4. **REM expectations fan** vs realized.

**Narrative framework.** The story is the **"last mile."** Headline disinflation from 25% to ~4% MoM is the easy part (kill money printing, anchor FX). Grinding from 4% to <2% is the hard part — it's services/wage inertia and requires the FX anchor to keep biting, which *requires* reserves (§2) to defend it. So inflation and reserves are coupled: cheap disinflation today is borrowed against the reserve stock. The market threshold: **core MoM re-accelerating above the band slope** breaks the REER and the narrative simultaneously. A core MoM that prints with a "1-handle" sustainably is a regime-confirmation event.

**Bull/bear flags.**
- 🟢 Core MoM below band slope and falling; REM expectations anchoring lower; services inflation finally cracking.
- 🔴 Core MoM re-accelerating or sticky above the crawl while tariffs still have catch-up to do; REM expectations un-anchoring; the gap between official disinflation and private trackers widening (data-credibility risk).

**Cross-section linkages.** Inflation − band slope = REER drift (§3). Inflation deflates wages (§11) and the fiscal accounts (§6, where inflation both erodes real spending — the "licuadora" — and is the implicit adjustment tool). It sets the floor on the peso curve's real rate (§8).

**Bottom line.** *"Core is running [X]% MoM annualizing to [Y]%; this is [above/below] the band slope, so the peso is [appreciating/depreciating] in real terms at [Z]%/yr. The anchor is [holding/slipping]."*

---

## 6. Fiscal Balance & the Quasi-Fiscal

**Purpose & analytical hook.** *"Is the fiscal anchor — the bedrock of the whole program — durable, or is it being held up by one-offs and inflation erosion that will reverse?"* The flow is largely solved; the question is *quality and durability*, plus the *quasi-fiscal* tail that migrated to the Treasury.

**Key metrics.**
- **Primary balance** — monthly, ARS, % of GDP, and **rolling 12m** (the durability gauge). MECON / Secretaría de Hacienda, monthly.
- **Financial (overall) balance** — primary minus interest; the harder target. The government's claim to *financial* (not just primary) surplus is a key credibility marker.
- **Revenue composition** — separate **structural** (VAT, income tax — tied to activity) from **cyclical/one-off** (the **PAIS tax** wind-down, the **blanqueo/**tax-amnesty windfall, export-duty timing). One-off-flattered surpluses are lower quality.
- **Expenditure composition** — what's being compressed: capital expenditure (capex — the "easy" but growth-killing cut), pensions (the largest line, politically explosive, partly indexed), subsidies (energy/transport tariff reform), public wages, transfers to provinces. **Distinguish real cuts from inflation erosion (licuadora).**
- **Quasi-fiscal** — post-reform, the BCRA's remunerated-liability burden (LELIQ→Pases→**LEFI**) was moved to the **Treasury**. Track the **LEFI/LECAP interest bill** as part of the true consolidated deficit. The "déficit cero" is cleaner only if the quasi-fiscal isn't just relocated. Track the consolidated (Treasury + BCRA) balance.
- **Provincial finances** — aggregate provincial primary balance; provinces can blow a hole the nation doesn't see.

**Chart specifications.**
1. **Rolling 12m primary & financial balance, % GDP**, 36m — the durability chart with the 2023 deficit baseline marked.
2. **Revenue quality** — stacked, structural vs one-off, 18m (watch the PAIS/blanqueo cliff).
3. **Expenditure by line, real terms YoY** — to expose where the adjustment fell and whether capex collapse is the (unsustainable) crutch.
4. **Consolidated balance** including quasi-fiscal interest — the "true" deficit.

**Narrative framework.** The fiscal anchor is the program's crown jewel and the most *over-celebrated* number. The analyst's job is skepticism on *quality*: How much of the surplus is (a) capex compression that can't continue without strangling growth, (b) pension licuado by inflation that reverses as disinflation succeeds (the cruel feedback: winning on inflation *raises* real pension spending), and (c) one-off taxes that are expiring? The durable surplus is the structural-revenue-minus-rigid-spending core. Turning point: the first month the 12m rolling primary turns down materially is a thesis-relevant event.

**Bull/bear flags.**
- 🟢 12m rolling primary holding ≥~1.5% GDP *and* financial balance positive; surplus increasingly from structural revenue and durable spending reform (subsidy/tariff) rather than licuadora/capex; provinces in line.
- 🔴 Surplus shrinking as one-off taxes expire and disinflation re-inflates pensions; capex at unsustainable lows masking the gap; quasi-fiscal interest re-expanding; provincial slippage.

**Cross-section linkages.** The fiscal surplus is what allows the **Treasury to buy reserves** (§2) and to avoid monetary financing (§8). Pension/wage compression is the political-tolerance variable (§11, §13). Disinflation (§5) mechanically *raises* real social spending — fiscal and inflation are coupled in a way that gets *harder*, not easier, as the program succeeds.

**Bottom line.** *"The 12m primary is [X]% GDP, [improving/eroding]; quality is [high/low] because [structural vs one-off]; consolidated (incl. quasi-fiscal) it is [Y]%. The anchor is [durable/fragile]."*

---

## 7. Debt & the Financial Program

**Purpose & analytical hook.** *"Can Argentina pay what's due in hard currency over the next 24 months without a market accident or a reserve raid — and is the curve pricing that correctly?"* This is the section that maps directly onto the Globals/Bonares trade.

**Key metrics.**
- **Hard-currency maturity wall** — sovereign Globals & Bonares coupons + amortizations by date, next 24 months, USD. The cluster dates (typically January and July semi-annual coupons + step-up amortizations) are the report's recurring stress points.
- **FX coverage ratio** — Net-Net reserves (§2) ÷ next-12m hard-cy sovereign payments. The accident gauge.
- **IMF program** — EFF size, disbursement calendar tied to reviews, NIR/fiscal performance criteria, outstanding repurchase schedule to the Fund itself (Argentina pays the *old* SBA back while drawing the new EFF — net IMF flow matters).
- **BOPREAL** — the BCRA-issued bonds that cleared importer/dividend arrears (Series 1/2/3): outstanding stock, amortization schedule, holder base, and **secondary price** (a real-time confidence read on BCRA credit).
- **Peso debt rollover** — monthly Treasury (LECAP/BONCAP/CER) maturities, **rollover (rollover ratio)** at each auction, and the **cost (cut-off yields)**. A failed/partial rollover forces either monetary financing (§8, inflationary) or a sharp rate spike. Track the auction calendar.
- **Country risk (EMBI+ Argentina)** — spread level and vs EM peers; the market's summary verdict.
- **Curve shape** — Global bond price/yield by maturity; the **slope** (deeply inverted/distressed vs normalizing) encodes default-timing expectations.

**Chart specifications.**
1. **Hard-currency maturity wall** — monthly bars, 24m, sovereign + BOPREAL + net IMF, colored by currency.
2. **FX coverage ratio** over time — Net-Net ÷ 12m payments, with the 1.0x line.
3. **EMBI+ Argentina vs EM peers** (e.g., index + comparable single-Bs), 24m.
4. **Global bond curve** — price by maturity, this week vs 4 weeks ago.
5. **Peso rollover ratio & cut-off yields** — bar + line, last 12 auctions.

**Narrative framework.** Two separate risks: **hard-currency** (a payment the reserves can't cover → §2 is the binding input) and **peso** (a rollover failure → §8 monetary consequence). The bullish thesis is *normalization*: spreads compressing toward single-B peers, the curve dis-inverting, regaining market access to refinance the wall rather than paying it out of reserves. The bearish thesis is the **wall meets the bleed** — a January/July payment cluster arriving while NIR is below the IMF path. The IMF program is the bridge that's supposed to get Argentina to market access before the reserves run out — track whether that bridge is intact (reviews passing, disbursements flowing).

**Bull/bear flags.**
- 🟢 EMBI compressing toward peers; curve dis-inverting; successful peso rollovers >100% at falling yields; IMF reviews passing on schedule; credible signs of regaining external market access (a successful new issue would be a major confirmation).
- 🔴 FX coverage <1.0x into a payment cluster; peso rollover <100% (Treasury injecting pesos → §8); IMF review delayed/waiver needed (→ §2 NIR miss); BOPREAL price falling; spreads widening vs peers (idiosyncratic stress, not just beta).

**Cross-section linkages.** Hard-cy payments *drain* §2 directly (the debt-service line in the reserve bridge). Peso rollover failure *forces* §8 (monetary financing) and feeds back to §5 (inflation). IMF reviews are gated by §2 (NIR) and §6 (fiscal) performance criteria — §7 is where those two sections get *priced*. This section is the most direct macro→asset-price transmission; it feeds §14 almost mechanically.

**Bottom line.** *"FX coverage of the 12m wall is [X]x; the next cluster is [date] for $[Y]bn against NIR of $[Z]bn. Market access is [open/shut]. We are [long/short/neutral] the [specific bond], expressed [duration/curve], invalidated if [trigger]."*

---

## 8. Monetary & Peso Curve *(added section)*

**Purpose & analytical hook.** *"Is the peso being remonetized in a healthy, demand-led way, or is liquidity being force-fed/starved — and what does the peso carry trade look like risk-adjusted?"* The peso curve is where the fiscal, inflation, and FX stories collide into a tradable rate.

**Key metrics.**
- **Monetary base & the "broad" aggregates** — and the framework BCRA is running (post-LEFI, base-money targeting / "emisión cero" rhetoric). Track base growth vs nominal GDP — remonetization from a historically tiny base is part of the bull story, but its *source* matters (FX purchases = healthy; Treasury financing = unhealthy).
- **Real money demand** — M2/M3 in real terms; a *rising* real money demand is the confidence tell (people willing to hold pesos again).
- **Policy rate & the short peso curve** — LECAP/LEFI yields; the **TEM** (monthly effective rate).
- **Ex-ante real rate** — policy/short rate minus REM-expected inflation. Positive and stable = orthodox; deeply negative = either confidence (low inflation expectations) or repression.
- **The carry trade ("carry / tasa vs dollar")** — peso rate vs expected band crawl + brecha risk. This is the flow that *funds* reserve accumulation (the "blend"/carry that brings dollars in) but reverses violently — the classic Argentine **carry-unwind** risk.
- **CER vs fixed breakeven** — links to §5.

**Chart specifications.**
1. **Real money demand (M2 real)**, 24m — the remonetization/confidence chart.
2. **Ex-ante real rate**, 18m — short rate minus expected inflation.
3. **Peso curve** (LECAP/CER), this week vs 4 weeks ago.
4. **Carry-vs-crawl** — implied carry return vs the band slope (the "is the carry trade still on" gauge).

**Narrative framework.** Healthy remonetization (rising real money demand funded by FX purchases) is a quiet but powerful bull signal — it means peso confidence is returning and BCRA can buy reserves without inflation. The fragility is the **carry trade**: foreign and local money sits in high peso rates betting the band holds; if the band cracks or the brecha jumps, the carry unwinds, dollars flee, and §2/§3 break together. So §8 is both an engine of the bull case and a hidden accelerant of the bear case.

**Bull/bear flags.**
- 🟢 Real money demand rising; positive, stable ex-ante real rate; peso curve normalizing/extending in tenor; carry attractive *and* funded by genuine inflows.
- 🔴 Liquidity force-fed by peso rollover failures (§7); real rate deeply negative *with* rising inflation expectations; carry-unwind signs (brecha widening, futures pricing devaluation > band, short rates spiking to defend the peso).

**Cross-section linkages.** Healthy base growth comes from §2 FX purchases; unhealthy growth from §7 rollover failures. The carry trade is the §2 inflow engine and the §3 reversal risk. Real rate is set against §5 expectations. This section is the connective tissue between the anchors and the spine.

**Bottom line.** *"Remonetization is [demand-led/forced]; the ex-ante real rate is [+/−X]%; the carry trade is [on/at risk]. The peso curve is [normalizing/stressed]."*

---

# PART III — THE REAL ECONOMY

---

## 9. Real Activity — GDP & EMAE

**Purpose & analytical hook.** *"Is the recovery real and broad, and crucially — is it the kind of recovery that *helps* the external accounts (export/investment-led) or *hurts* them (consumption/import-led)?"* For Argentina, growth is double-edged: it buys political runway (§13) but pulls in imports and drains reserves (§2/§4).

**Key metrics.**
- **EMAE** — monthly activity proxy, headline + 15-sector breakdown; YoY and the cleaner **MoM SA / 3m-3m annualized**. INDEC, monthly (~6-week lag).
- **GDP** — quarterly, YoY and QoQ SA, with expenditure components **C + I + G + NX**. INDEC.
- **Investment (IBIF/FBKF)** — and its composition: **construction vs durable equipment (esp. imported machinery)**. Equipment investment = future capacity = high-quality recovery; construction = more domestic/cyclical.
- **High-frequency confirms** — VAT collection real (a near-real-time consumption proxy from §6), auto production/sales (patentamientos), cement dispatches, energy demand.

**Chart specifications.**
1. **EMAE** — level (SA) + YoY, 36m, with the recession trough and recovery annotated.
2. **EMAE sector heatmap** — YoY by sector, to show breadth (is it just agro/energy rebounding, or broad?).
3. **GDP expenditure contribution** — stacked QoQ contributions of C/I/G/NX.
4. **Investment composition** — construction vs equipment, and imported-equipment share (the dollar-quality read).

**Narrative framework.** Diagnose the recovery's *composition*. An **investment- and export-led** recovery is sustainable and BoP-friendly (bullish on every axis). A **consumption-led, import-heavy** recovery is the historical Argentine trap — it feels good, wins elections, and walks straight into a BoP wall (the §2 drain). The "two clocks" framing lives here too: is the structural-tradeable economy (§10) growing faster than import-intensive domestic demand? Turning points: the recovery broadening from agro/energy into industry/services = healthy; or stalling/double-dipping under the weight of real rates and fiscal compression = political-runway risk.

**Bull/bear flags.**
- 🟢 EMAE 3m/3m positive and broadening across sectors; investment (esp. equipment) leading; recovery led by tradeables.
- 🔴 Recovery narrow (only agro/energy) or stalling; consumption-led with import surge (pre-warns §2 drain); construction-only investment; activity rolling over into the election window (§13 risk).

**Cross-section linkages.** Activity *drains* reserves via imports (§2/§4) — flag this when EMAE accelerates. It's *funded* by credit (§12) and constrained by real rates (§8). It determines structural tax revenue (§6). It is the raw material of political tolerance (§11/§13). Tradeable-led growth ties to §10.

**Bottom line.** *"Activity is [growing/stalling] at [X]% 3m/3m, [broad/narrow], led by [component]. This recovery is [BoP-friendly / BoP-draining]."*

---

## 10. Production & Energy — *The Structural-Dollar Engine*

**Purpose & analytical hook.** *"How fast is the structural dollar engine — energy, mining, agriculture — being built, and will it arrive before the financing wall?"* This is the section that justifies a *multi-year* bull case independent of the cyclical fragility. It is the answer to "why isn't Argentina just another EM crisis."

**Key metrics.**
- **Oil & gas production** — total and **Vaca Muerta** specifically (the shale play); barrels/day and gas. Secretaría de Energía monthly.
- **Energy exports** — volumes and **USD value**; and the **net energy trade balance** (the swing from deficit to surplus is *the* structural story — restate from §4).
- **Infrastructure bottleneck trackers** — pipeline capacity (e.g., the trunk pipelines), export terminal capacity, LNG project status. Energy *production* growth is only a dollar story if the *export infrastructure* exists; track the bottleneck.
- **Mining (lithium, copper) & RIGI pipeline** — committed large-scale projects under the investment-incentive regime; lithium output; the multi-year copper pipeline.
- **IPI (industrial production)** — INDEC, by sub-sector (the cyclical, often import-competing, domestic economy — the *other* clock).
- **ISAC (construction)** — INDEC; public-works-sensitive (links to §6 capex cuts).
- **Agriculture** — current campaign crop estimates (soy, corn, wheat) vs prior year and the drought baseline; ties to the §4 settlement calendar.

**Chart specifications.**
1. **Vaca Muerta production**, 36m+, with the energy-balance swing overlaid — the hero structural chart.
2. **Energy export USD value** + net energy balance, multi-year.
3. **Two-speed economy** — IPI (cyclical/industry) vs energy+mining+agro (structural/tradeable), indexed to show the divergence.
4. **Crop campaign estimate** — current vs prior 3 years.

**Narrative framework.** The bull thesis's foundation: Argentina is transitioning from a country that *imports* energy to one that *exports* it, and is adding lithium/copper/LNG on a multi-year horizon. This is a **secular** dollar inflow that, once large enough, structurally fixes the §2 constraint and ends the 80-year boom-bust BoP cycle. The bear/realist counter: the cyclical/financing clock (§2/§7) may hit the wall *before* the structural dollars are big enough, *and* infrastructure bottlenecks can delay the dollars by years. The report's deepest analytical job is **dating the crossover** — when does structural FX generation reliably exceed the cyclical drain. ISAC/IPI are the *other*, weaker clock — the import-competing domestic economy squeezed by an overvalued peso (§3) and capex cuts (§6).

**Bull/bear flags.**
- 🟢 Vaca Muerta output and energy exports compounding; pipeline/export capacity expanding on schedule; RIGI projects breaking ground; a strong crop campaign.
- 🔴 Energy growth capped by infrastructure delays; RIGI pipeline stalling on FX/regulatory uncertainty; drought or price collapse hitting the crop; IPI in sustained contraction (the overvalued-peso/recession squeeze on industry).

**Cross-section linkages.** Energy/mining/agro exports are the *structural* feed to §2/§4. IPI/ISAC weakness ties to §3 (overvaluation hurting industry) and §6 (capex cuts hurting construction). RIGI is a §13 policy-credibility product. This section is where the multi-year bull case is sourced; §2 is where the cyclical fragility lives — the report's central tension is between these two sections.

**Bottom line.** *"The structural dollar engine is [accelerating/bottlenecked]; the energy balance is [+$Xbn and widening]. Crossover (structural FX > cyclical drain) is [arriving / still 12–24m out]."*

---

## 11. Labor Market & Real Wages

**Purpose & analytical hook.** *"How much adjustment can the population still absorb — i.e., how much political runway (§13) does the stabilization have left?"* Real wages and employment are the **social shock-absorber gauge**; when it's exhausted, the politics (and thus the reform) break.

**Key metrics.**
- **Real wages** — RIPTE / Índice de Salarios (INDEC), deflated by CPI (Fisher-adjusted), split **registered private / public / informal**. Registered private recovers first and fastest; informal lags worst.
- **Formal employment (SIPA)** — registered private employment level and trend (the durable-jobs gauge).
- **Wage-productivity gap** — real wage growth vs productivity growth; real wage gains *backed* by productivity are non-inflationary and durable; gains running ahead of productivity are an inflation/competitiveness risk.
- **Unemployment & underemployment** — INDEC EPH, quarterly.
- **Poverty & indigence rate** — INDEC, semi-annual; the headline social-cost number that drives §13.
- **Informality share** — the structural weakness; proxies for the informal economy.

**Chart specifications.**
1. **Real wages by segment**, 24m, indexed to the Milei start — the "who's recovering" chart with the early-2024 collapse and the recovery path.
2. **Registered private employment (SIPA)**, 36m.
3. **Real wage vs productivity**, indexed — the durability test.
4. **Poverty rate**, semi-annual bars, with the H1-2024 spike marked.

**Narrative framework.** The early shock (sharp real-wage collapse, poverty spike in H1-2024) was the *cost* of stabilization; the recovery path is the *payoff*. The political-economy question: are real wages and employment recovering *fast enough* to keep social tolerance ahead of reform fatigue, especially through the electoral calendar (§13)? The cruel coupling with §5/§6: disinflation *helps* real wages (good for tolerance) but re-inflates pension spending (bad for fiscal). Turning point: registered real wages back above the pre-Milei (or pre-2023-crisis) level = the government can credibly claim the adjustment "worked."

**Bull/bear flags.**
- 🟢 Registered real wages recovering and above pre-shock levels; formal employment growing; wage gains productivity-backed; poverty falling back toward/below pre-shock.
- 🔴 Real wages stalling below pre-shock with employment flat/falling; informal sector left behind; poverty sticky-high into the election → social-tolerance exhaustion → reform-reversal risk.

**Cross-section linkages.** Real wages are deflated by §5 and drive §12 (consumption). Employment durability validates §9's recovery quality. The whole section is the *input* to §13's political-runway assessment. Pension indexation links the social story to §6's fiscal durability.

**Bottom line.** *"Registered real wages are [above/below] pre-shock and [rising/flat]; the social shock-absorber has [room/is stretched]. Political runway is [lengthening/shortening]."*

---

## 12. Consumption & Credit

**Purpose & analytical hook.** *"What is powering domestic demand — sustainable income recovery, a credit impulse, or a one-off savings drawdown — and how much does it threaten the external accounts?"* Consumption is the largest GDP component and the most import-intensive; its *driver* determines whether the recovery is durable or a BoP threat.

**Key metrics.**
- **Private consumption** — from §9 GDP, plus high-frequency proxies: retail sales (CAME), supermarket/wholesale sales (INDEC), consumer durables, patentamientos (auto registrations).
- **Real credit to the private sector** — by category: **mortgage (UVA), personal, credit-card, SME/commercial, corporate**. The post-stabilization **credit boom from a tiny base** is a key recovery driver. BCRA monetary statistics.
- **Credit/GDP** — still among the lowest in the region (~single-digit %); the normalization runway is the structural growth call, *but* credit-led demand is import-intensive and reserve-draining if it outruns income.
- **Deposits** — peso and **USD** deposits; USD-deposit trend is a confidence/cepo read (rising USD deposits post-amnesty/cepo-lift = dollars entering the system, supports §2's gross via encajes — but it's *borrowed* not earned, see §2).
- **Credit-wage spread** — real credit growth vs real wage growth; credit racing far ahead of wages = leverage-funded (less sustainable) demand.

**Chart specifications.**
1. **Real credit by category**, 18m — the credit-impulse chart, mortgage (UVA revival) highlighted.
2. **Credit/GDP** vs regional peers — the structural runway.
3. **Real credit vs real wages** — the sustainability spread.
4. **USD deposits**, 18m — the confidence/system-dollarization read.

**Narrative framework.** Three-driver diagnosis: **wage-led** (durable, the bull case), **credit-led** (powerful from a low base but turns import-hungry and needs financing), or **savings-drawdown** (one-off, unsustainable). A credit recovery from Argentina's ultra-low base is genuinely bullish *for growth* but ambiguous *for reserves* — it pulls imports and, if funded by USD deposits, builds a peso/dollar mismatch. The mortgage (UVA) revival is a special signal: long-duration peso lending only happens when people believe inflation will stay low — its return is a powerful **disinflation-credibility** confirmation.

**Bull/bear flags.**
- 🟢 Consumption recovery wage-led; credit growing from a low base *in line with* income; UVA mortgages reviving (disinflation-credibility tell); USD deposits stable/rising as genuine inflows.
- 🔴 Demand credit-led and outrunning wages (leverage build); savings-drawdown-driven (unsustainable); credit-fueled import surge pre-warning §2; USD-deposit flight (confidence crack).

**Cross-section linkages.** Consumption is the import-intensive driver behind §9's recovery quality and §2/§4's import drain. It's powered by §11 (wages) and §8 (credit/rates). UVA mortgage revival validates §5 (disinflation credibility). USD deposits feed §2 gross reserves (as encajes — *borrowed*).

**Bottom line.** *"Domestic demand is [wage-led/credit-led/drawdown-led]; the credit impulse is [sustainable/outrunning income]; this is [neutral/threatening] for reserves. The UVA-mortgage revival [does/does not] confirm disinflation credibility."*

---

# PART IV — THE META-LAYER

---

## 13. Regime & Political Risk

**Purpose & analytical hook.** *"What is the probability that the reform program continues vs reverses, and what events in the next 3–12 months could break or confirm it?"* Every number in the report is conditional on the regime surviving; this section prices that condition.

**Key metrics.**
- **Government legislative strength** — seat counts in both chambers, working coalition, and the **post-October-2025-midterm** balance (the single biggest political variable — did the government gain enough seats to govern/reform, or is it still negotiating bill-by-bill?).
- **Presidential approval & "imagen"** — multiple pollsters, level and trend; the implicit mandate for continued adjustment.
- **Reform pipeline status** — labor reform, tax reform, pension reform, privatizations, RIGI uptake — what's passed, stuck, or at risk.
- **Governor/provincial relations** — the federal-revenue-sharing (coparticipación) fights; provincial alignment (links to §6).
- **Social-conflict trackers** — strike calendar (CGT general strikes), protest frequency/intensity, the piquetero dynamic.
- **Dollarization probability** — track the conditions: is it still on the table as policy, and what would trigger a move (and what it would require — reserves Argentina doesn't have, hence the conditionality).
- **Event calendar** — IMF review dates, bond payment clusters, BCRA decisions, elections, key bill votes, budget process.

**Chart specifications.**
1. **Approval trend**, multi-pollster, since inauguration, with key events annotated.
2. **Legislative balance** before/after the midterm — seats by bloc.
3. **Social-conflict index** (strikes/protests), monthly — the tolerance-exhaustion gauge (ties to §11).
4. **The master event calendar** — a Gantt of the next 8 weeks' catalysts (this also feeds the cover).

**Narrative framework.** The reform is a race against **political capital depletion**. Capital is *spent* on adjustment (real-wage pain, §11) and *replenished* by results (disinflation success, §5; recovery, §9). The midterm was the referendum on whether the public would fund a second phase of reform. The analyst's job: convert the qualitative politics into a **reversibility probability** — how locked-in are the gains (fiscal anchor, FX framework) vs how easily could a future congress/government unwind them. Dollarization should be treated as a low-probability *tail* whose main function is as a rhetorical anchor and a reflection of FX-regime distrust, not a base case (it requires a reserve stock Argentina lacks — §2).

**Bull/bear flags.**
- 🟢 Midterm strengthened the governing bloc; approval resilient despite adjustment; reform pipeline advancing; social conflict contained; the framework increasingly viewed as irreversible.
- 🔴 Approval eroding with adjustment fatigue (§11 exhausted); reforms stalling in a hostile congress; escalating social conflict; rising reversal/discontinuity risk priced into the curve (§7) — *political risk is the ultimate source of the tail in every other section.*

**Cross-section linkages.** Politics is *funded* by §5/§9/§11 (results) and *spent* on §6/§11 (adjustment pain). It gates §7 (IMF reviews need political delivery of fiscal/structural conditions) and §10 (RIGI investment needs policy credibility). It is the master conditioning variable: every other section's bull case assumes regime continuity, which this section prices.

**Bottom line.** *"Reform continuity probability is [high/medium/low] post-midterm; political capital is [replenishing/depleting]; the binding political catalyst in the next quarter is [event]. Reversal risk is [priced/mispriced] in the curve."*

---

## 14. Asset-Price Dashboard & Positioning *(added section)*

**Purpose & analytical hook.** *"Given everything above, is Argentine risk cheap or rich, what's the cleanest trade expression, and how is the book positioned vs the view?"* A buy-side report must close the loop from macro to marks — otherwise it's a sell-side note. This section makes the report *actionable*.

**Key metrics / contents.**
- **Asset dashboard** — Globals (by maturity), Bonares (local-law $), BOPREAL, the peso curve (LECAP/CER), Merval in CCL terms, the brecha, ROFEX. Level, 1wk Δ, YTD, and **vs the macro fair-value the report implies.**
- **Macro-vs-market reconciliation** — the report's verdict (§1) vs what the price is implying. Is the market pricing more/less stabilization success than the data supports? This *gap* is the alpha.
- **Relative value** — Globals vs Bonares (jurisdiction spread), the Global curve shape, Argentina vs EM-peer spread (§7), peso carry vs hedged-dollar return.
- **Positioning & flows** — best-available reads on foreign positioning, ETF flows, the consensus narrative (to identify crowded trades to fade).

**Chart specifications.**
1. **Asset dashboard table** — the one-glance marks board.
2. **Macro-fair-value vs market** — a simple cheap/rich gauge for the GD/AL curve vs the report's verdict.
3. **RV scatter** — Argentina vs single-B EM peers (spread vs rating/reserves).

**Narrative framework.** Translate the macro into a price view: when the data-driven verdict (§1) is more constructive than the market's implied probability, lean long; when reserves/politics are deteriorating faster than spreads admit, fade the rally. Be explicit about the *expression* (duration, curve, jurisdiction, FX vs credit) and the *invalidation level*.

**Bull/bear flags.** 🟢 Market pricing *less* stabilization than the data supports + reserves on-track → add risk. 🔴 Market pricing *more* than the data supports + NIR red → reduce/short.

**Cross-section linkages.** This is the integral of the entire report. §7 feeds the credit view, §2/§3 the FX view, §8 the peso-carry view, §13 the tail.

**Bottom line.** *"The market is pricing [more/less] stabilization than our verdict supports; the cleanest expression is [trade]; invalidation at [level]."*

---

## 15. Risk Register & Trade Expression

**Purpose & analytical hook.** A standing table of the top macro risks so the PM sees the tail explicitly, every week, and watches it migrate.

**Format — the Risk Register (top 5–7 rows):**

| Risk | Probability | Severity (asset impact) | Time horizon | Lead indicator (which section) | Δ vs last week |
|---|---|---|---|---|---|
| NIR misses IMF target → waiver/review delay | … | … | next test date | §2 NIR vs path | … |
| Disorderly devaluation / band break | … | … | seasonal trough | §3 brecha + futures-band spread | … |
| Disinflation last-mile stalls / re-accelerates | … | … | 1–3m | §5 core MoM | … |
| Peso rollover accident → monetary financing | … | … | next auction | §7/§8 rollover ratio | … |
| Political/reform reversal | … | … | 3–12m | §13 approval + congress | … |
| Drought / commodity-price shock to agro dollars | … | … | harvest window | §4/§10 crop + prices | … |

**Narrative framework.** Each risk carries its **single lead indicator** (which section to watch) and a **probability that moves week to week**. The register's discipline is that nothing in it is a surprise — each risk is mapped to a section that's already tracking its trigger. End with the **explicit trade expression** of the current verdict and the **invalidation levels** that would flip it.

**Bottom line.** *"The dominant risk this week is [X], probability [rising/falling]; the book is positioned [Y]; the single trigger that flips our verdict is [Z]."*

---

## Cross-Cutting Conventions (apply to every section)

- **30-second executive brief** opens each section — the one signal, stated as a directional call.
- **`WHAT CHANGED THIS WEEK` box** at the top of each section — the diff is the product.
- **Charts before tables.** Every chart carries a **signal glyph** (▲ improving / ▬ stable / ▼ deteriorating) plus a conviction shade (high/low), set by that section's flag logic — so the PM can read direction without reading prose.
- **Every section ends in a committed bottom-line call** with an explicit invalidation trigger. No hedging — a view plus the level that proves it wrong.
- **Earned vs borrowed discipline** (from §2) propagates everywhere: distinguish genuine improvement from financed/one-off/inflation-eroded improvement in fiscal, reserves, trade, and credit alike.
- **The two-clocks frame** (structural-dollar engine vs cyclical-financing wall) is the report's organizing tension — restate where the race stands on the cover and in §1.
- **Data-credibility footnote:** where official data is contested (CPI history, reserve definitions), show the official number *and* the analyst-adjusted one, and never silently change a methodology.

---

## Builder's note: two sections added to the original spec

The original required-section list is complete on the *real-economy* and *external* sides. A hedge-fund (vs sell-side) version adds two things:

- **§8 Monetary & Peso Curve** — the peso-debt rollover and carry trade are where a stabilization actually breaks in real time. Too central to fold into Fiscal or Debt.
- **§14 Asset-Price Dashboard** — the report has to end at a mark and a trade, not a verdict.

If a leaner build is preferred, §8 can fold into §7 and §14 into §1, but that sacrifices the two most *tradable* parts of the document.
