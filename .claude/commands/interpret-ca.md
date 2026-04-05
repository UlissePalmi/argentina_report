Read the files `data/external/imf_current_account.csv`, `data/external/indec_trade.csv`, `data/external/bcra_reserves.csv`, and `data/external/bcra_fx.csv`, then write a structured analytical interpretation of Argentina's external dollar situation.

---

## Conceptual framework

### The current account has four components
| Component | What it measures | Argentina's typical sign |
|---|---|---|
| Goods balance | Exports - imports of physical goods | Positive (surplus) |
| Services balance | Tourism, freight, financial services | Negative (~$2-2.5B/quarter) |
| Primary income | Interest payments, profit remittances | Strongly negative (~$3-4B/quarter) |
| Secondary income | Remittances and transfers | Small positive |

A goods surplus does NOT mean Argentina is accumulating dollars. Always interpret the TOTAL current account, not just the trade balance.

### Gross vs net reserves — always use net
| Measure | What it includes |
|---|---|
| Gross reserves | Everything BCRA holds (~$30-35B typical) |
| Net reserves | Gross minus IMF debt, China swap (~$5B, not usable), bank FX deposits (~$9-12B, belong to depositors) |

Net reserves below zero means no buffer. Any shock goes directly to the exchange rate.

### Real exchange rate dynamic
If monthly CPI inflation > crawling peg depreciation rate for multiple consecutive months, real appreciation accumulates → exports less competitive, imports cheaper → trade surplus erodes over time. Flag this explicitly when present.

---

## Thresholds to flag

**Current account:**
- Surplus: improving — note which component is driving it
- Deficit $0–3B/quarter: monitor
- Deficit >$3B/quarter: deteriorating — flag as concerning
- Deficit >$5B/quarter: critical — flag as warning

**Trade balance:**
- Annual surplus <$5B: external pressure building
- Import growth >20% YoY with flat exports: real FX appreciation eroding competitiveness — flag explicitly
- Export growth >15% YoY: positive — note if volume-driven (structural) or price-driven (temporary)

**Net reserves:**
- Above $5B: comfortable buffer
- $0–5B: thin — monitor closely
- Negative: critical — flag prominently, note upcoming payments
- Below –$5B: severe stress, crisis risk elevated

**Context for 2024–2025:**
- 2024 trade surplus ~$19B: exceptional — compressed imports (depressed economy) + strong harvest recovery
- 2025: imports surging (+30%+ YoY) as economy recovered and real exchange rate appreciated — surplus shrinking
- Always compare against this 2024 baseline

---

## Report structure

Answer these four questions in order:

1. **Flow** — Is the current account in surplus or deficit this quarter? What is the trend over the last 4 quarters?

2. **Stock** — What are gross reserves right now? Are they improving or deteriorating over the last 6 months? Note that net reserves (not in the data) are materially lower — flag this caveat.

3. **Upcoming pressure** — Note that annual external debt service is ~$20B in 2026, with key payment months in January and July. Net reserves must always be read relative to upcoming payments.

4. **Structural risk** — Is import growth outpacing exports? Is the real exchange rate dynamic eroding the trade surplus? Use the FX rate trend from `bcra_fx.csv` to assess direction.

---

## Output format

Write in flowing analytical prose, not bullet points. Keep it under 250 words. Use specific numbers from the data files. End with a one-sentence bottom line using one of these templates:

- **Improving:** *"Dollar inflows exceeded outflows in Q[X], with the current account returning to surplus driven by [driver]. Gross reserves improved to $[X]B, though net reserves remain thin relative to $[X]B due in [month]."*
- **Deteriorating:** *"Argentina continued to lose dollars in Q[X], with the current account deficit widening to $[X]B as [driver]. Gross reserves at $[X]B provide minimal buffer ahead of $[X]B in payments due [month]."*

Be analytical, not descriptive. Give a clear directional call — improving or deteriorating — and explain the mechanism, not just the number.
