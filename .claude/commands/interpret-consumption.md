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

From `consumption.csv`, read `consumer_credit_yoy_pct` (consumer + personal loans) and `total_credit_yoy_pct` (all private loans) for the last 6 months.

Key comparison: **consumer_credit_yoy_pct vs nominal_wage_yoy_pct**

Interpret:
- **credit YoY < wage YoY:** Credit is growing in line with or slower than incomes → consumption is not leverage-driven. Low concern.
- **credit YoY > wage YoY by 5–15pp:** Households are leveraging up moderately. Monitor.
- **credit YoY > wage YoY by >20pp:** Credit is clearly outpacing income growth → households borrowing to maintain consumption. Flag explicitly.
- **credit YoY > 100%:** In Argentina's high-inflation context, check whether this is real growth or just nominal. If CPI is also 100%+, real credit growth may be flat or negative — state this explicitly.

**Important inflation adjustment:** In Argentina, nominal credit growth must always be compared against CPI to assess real growth. Real credit growth = consumer_credit_yoy_pct − cpi_yoy_pct. If real credit growth is negative despite high nominal growth, credit is actually contracting in real terms — this is deflationary for consumption.

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
