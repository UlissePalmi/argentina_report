Read the files `data/consumption/consumption.csv`, `data/inflation/indec_cpi.csv`, and `data/gdp/gdp_components.csv`, then write a structured analytical interpretation of what is driving private consumption in Argentina.

---

## The three-driver framework

Private consumption (C) can only grow through three mechanisms:

| Driver | What it means | Is it sustainable? |
|---|---|---|
| Real wage growth | Households earn more in purchasing-power terms | Yes — backed by productivity |
| Credit expansion | Households borrow to consume | Conditional — sustainable only if real wages are rising too |
| Savings drawdown | Households spend accumulated savings | No — temporary by definition |

Your job is to determine which of these three is dominant in the most recent data.

---

## Step 1 — Anchor: what is C actually doing?

From `gdp_components.csv`, read `C_pct` for the last 2–3 quarters. This is the quarterly YoY growth rate of real private consumption that you are trying to explain.

Note the trend: is C accelerating or decelerating? Is it above or below GDP growth (`GDP_pct`)?

---

## Step 2 — Real wages

From `consumption.csv`, read `nominal_wage_yoy_pct` for the last 6 months.
From `indec_cpi.csv`, read `cpi_yoy_pct` for the same months.

Compute: **real_wage_yoy ≈ nominal_wage_yoy_pct − cpi_yoy_pct**

Interpret:
- **real_wage_yoy > 0:** Real purchasing power is rising → sustainable consumption driver. Note whether the trend is strengthening or narrowing.
- **real_wage_yoy 0–3%:** Modest recovery — consumption supported but fragile.
- **real_wage_yoy < 0:** Real wages are contracting — households spending despite lower purchasing power. Flag: they must be funding consumption through credit or savings.
- **real_wage_yoy < −5%:** Serious erosion. Consumption growth in this context is almost entirely credit/savings-driven.

Use the most recent 3-month average to smooth noise from monthly volatility.

---

## Step 3 — Credit expansion

From `consumption.csv`, read the granular credit breakdown for the last 6 months:

| Column | Category | What it means |
|---|---|---|
| `real_personal_loans_pct` | Consumption | Personal loans — direct household spending |
| `real_credit_cards_pct` | Consumption | Credit cards — direct household spending |
| `real_mortgages_pct` | Asset | Housing investment |
| `real_auto_loans_pct` | Asset | Auto purchase |
| `real_overdrafts_pct` | Business | Working capital for firms |
| `real_commercial_paper_pct` | Business | Commercial financing |

Also read `real_personal_loans_mom_pct`, `real_credit_cards_mom_pct`, `real_overdrafts_mom_pct`, `real_commercial_paper_mom_pct` for MoM signals.

**3a — Consumption lending (personal loans + credit cards)**

Key comparison: consumption credit YoY vs real wage YoY.

- **consumption credit YoY < real wage YoY:** Credit not outpacing incomes → low leverage concern.
- **consumption credit YoY > real wage YoY by 5–15pp:** Moderate leverage build-up. Monitor.
- **consumption credit YoY > real wage YoY by >20pp:** Households borrowing to consume. Flag explicitly.

**Base effect rule — apply before interpreting any YoY number:**

Argentina's credit market collapsed in 2019–2020 and again in 2023. Any series coming off a depressed base will show mechanically high YoY even if the recovery is slowing. Use this three-step check:

**Step 1: Check MoM — is the level still growing?**
- MoM positive → normalization; YoY deceleration is mechanical, not alarming
- MoM negative → genuine contraction; flag regardless of YoY level

**Step 2: Compare level to pre-crisis trend**
- Is the current level above, at, or below where it would have been without the crisis?
- If still below trend → more room to normalize; high YoY reflects catch-up, not new leverage
- If back at or above trend → normalization complete; further growth is new leverage

**Step 3: Only after steps 1 and 2 interpret the YoY number**

**3b — Business borrowing (overdrafts + commercial paper)**

Rising business credit is productive if it funds working capital and investment. It is a warning sign if firms are borrowing to cover operating losses (roll-over of distressed debt).

- **business credit YoY >> consumption credit YoY:** Credit expansion is firm-led, not household-led. Less inflationary for consumption, but monitor for firm distress if real rates are high.
- **business credit YoY << consumption credit YoY:** Households are the marginal borrower. Direct consumption implication.
- Apply the same base-effect three-step check to business credit before interpreting YoY.

**Important inflation adjustment:** All columns in `consumption.csv` prefixed with `real_` are Fisher-adjusted. Use only these. Nominal series are stored for reference but should not be used in interpretation.

---

## Step 4 — Savings drawdown

From `consumption.csv`, read `deposits_yoy_pct` (fixed-term peso deposits, system-wide).

Fixed-term deposits are the most liquid formal savings vehicle for Argentine households. Falling deposits suggest households are either:
1. Spending savings (dissaving)
2. Moving savings to dollars or real assets (not captured here)

Interpret:
- **deposits_yoy > CPI YoY:** Real deposits are growing → households are saving, not dissaving. Consumption is not savings-funded.
- **deposits_yoy roughly equal to CPI YoY (±10pp):** Real deposits roughly flat — neutral.
- **deposits_yoy < CPI YoY:** Real deposits declining → households accumulating less savings relative to inflation. Watch.
- **deposits_yoy < 0 in nominal terms:** Households are actively withdrawing savings → dissaving. Flag prominently.

**Caveat:** Always note that dollar deposits and real assets are not captured in this series. Falling peso deposits could reflect dollarization rather than consumption spending.

---

## Step 5 — Productivity check

From `consumption.csv`, read `emi_yoy_pct` (EMI industrial production index) for the last 6 months.

This helps distinguish wage-led consumption that is backed by output growth from wage-led consumption funded by redistribution or government transfers.

- **EMI positive and rising:** Industrial output is growing → real wage gains are plausibly productivity-backed. Most sustainable configuration.
- **EMI flat while wages rise:** Wage gains are service-sector or transfer-driven, not manufacturing productivity. Sustainable in the short term, but limits how far real wages can rise without inflation pressure.
- **EMI negative:** Manufacturing is contracting even as wages rise → wage gains are concentrated in services. Note two-speed economy.

Cross-check with `emae.csv` sectoral data if available for deeper decomposition.

---

## The three configurations — bottom-line call

After reading all four signals, categorize the current configuration as one of:

**Configuration A — Wage-led (healthy):**
Real wages positive AND credit growing at or below wage growth AND deposits stable or rising.

Bottom line template:
*"Private consumption grew [C_pct]% YoY in Q[X], driven by real wage recovery of [real_wage]% (nominal wages [nominal_wage]% minus CPI [cpi]%). Consumer credit is [credit]% YoY — [above/below] wage growth — suggesting households are [leveraging up/not leveraging]. Deposits are [deposits]% YoY, consistent with [saving/neutral/dissaving]. This is a wage-led consumption cycle backed by [rising/flat] industrial output — the most sustainable configuration."*

**Configuration B — Credit-led (monitor):**
Credit growing materially faster than real wages, OR real wages marginally positive but credit accelerating.

Bottom line template:
*"Private consumption grew [C_pct]% YoY in Q[X], but the driver is credit expansion. Consumer credit is [credit]% YoY against nominal wage growth of [nominal_wage]% (real wages [real_wage]%). Households are borrowing to consume — real credit growth is [real_credit]% after adjusting for inflation. Deposits are [deposits]% YoY. Watch for credit quality deterioration if real wages do not catch up within 2–3 quarters."*

**Configuration C — Savings drawdown (fragile):**
Real wages negative AND deposits falling in real or nominal terms.

Bottom line template:
*"Private consumption grew [C_pct]% YoY in Q[X] despite real wage contraction of [real_wage]% (nominal [nominal_wage]% minus CPI [cpi]%). Fixed-term deposits are [deposits]% YoY [in nominal terms / in real terms after inflation], suggesting households are drawing down savings. Consumer credit at [credit]% YoY [is/is not] providing additional support. This configuration is unsustainable — consumption will compress once savings buffer is exhausted unless real wages recover."*

---

## Output format

Write in flowing analytical prose, not bullet points. Use specific numbers from the data. Keep it under 300 words. Structure: Anchor → Real wages → Credit → Savings → Productivity → Bottom-line call.

Always state clearly which of the three configurations (wage-led, credit-led, savings drawdown) best describes the current moment. Do not hedge — give a directional call.
