/* global React */
/* Shared sample data — fictional macro outlook (placeholder for pipeline) */

const SAMPLE = {
  firm:       "Halford & Reade",
  desk:       "Global Macro Strategy",
  city:       "London · New York · Singapore",
  date:       "27 May 2026",
  vol:        "Vol. XII · No. 5",
  issue:      "Macro Quarterly · Mid-Cycle Edition",
  title:      "Late-Cycle Crosscurrents",
  subtitle:   "Disinflation’s last mile meets a fiscal pivot — why H2 2026 rewards convexity, not conviction.",
  bottomline: "We move to Base from Bull. Add duration on weakness; trim equity beta into Q3 prints.",

  authors: [
    { name: "Iris Halford, CFA",   role: "Chief Strategist",       email: "ih@halfordreade.co" },
    { name: "Marcus Reade",         role: "Head, Rates & FX",       email: "mr@halfordreade.co" },
    { name: "Priya Achebe, PhD",    role: "Senior Economist",       email: "pa@halfordreade.co" },
  ],

  // Exec thesis bullets
  thesis: [
    "Core services inflation has bent but not broken. We model OER reverting to 3.4% by Q4 — not 3.0% as consensus believes — keeping the Fed on a held footing through September.",
    "Fiscal impulse turns negative for the first time since 2022 as TCJA expirations bind. Our model pencils −0.6pp drag in 2027, front-loaded into Q4 2026.",
    "Cross-asset volatility is mispriced. 1y vol on rates trades at the 14th percentile; we recommend long-vol convex structures over directional bets.",
    "Risk: a benign disinflation print in July would force a hawkish-to-dovish repricing. We size for this asymmetry rather than against it.",
  ],

  // Scenario table
  scenarios: {
    cols: ["Bear", "Base", "Bull"],
    rows: [
      { label: "GDP, 2026e",       vals: ["+0.8%", "+1.7%", "+2.4%"], unit: "" },
      { label: "Core PCE, YE",     vals: ["3.4%",  "2.9%",  "2.4%"],  unit: "" },
      { label: "Fed Funds, YE",    vals: ["5.00%", "4.50%", "3.75%"], unit: "" },
      { label: "10Y UST, YE",      vals: ["4.85%", "4.20%", "3.65%"], unit: "" },
      { label: "S&P 500, YE",      vals: ["4,950", "5,720", "6,180"], unit: "" },
      { label: "EUR / USD, YE",    vals: ["1.02",  "1.11",  "1.18"],  unit: "" },
      { label: "Brent, YE ($/bbl)",vals: ["62",    "78",    "92"],    unit: "" },
      { label: "Probability",      vals: ["25%",   "55%",   "20%"],   unit: "", bold: true },
    ],
  },

  // Bull/base/bear projection (2y-fwd, quarterly)
  proj: {
    bear:    [4.50, 4.55, 4.65, 4.75, 4.80, 4.85, 4.85, 4.80, 4.75],
    base:    [4.50, 4.45, 4.35, 4.25, 4.20, 4.15, 4.10, 4.05, 4.00],
    bull:    [4.50, 4.30, 4.10, 3.95, 3.80, 3.70, 3.65, 3.60, 3.55],
    xLabels: ["Q2'26","Q3'26","Q4'26","Q1'27","Q2'27","Q3'27","Q4'27","Q1'28","Q2'28"],
  },

  // Headline indicator path (CPI YoY)
  cpiPath: {
    data: [9.1,8.5,7.7,6.5,6.0,5.0,4.2,3.7,3.4,3.2,3.1,3.0,2.9,2.8,2.6,2.7,2.6,2.5],
    xLabels: ["J22","J22","J23","J23","J24","J24","J25","J25","J26"],
  },

  // Cross-asset returns
  heatmap: {
    rows: ["S&P 500","NDX","STOXX","Nikkei","EM eq.","UST 10Y","Bund 10Y","HY credit","DXY","Gold","Brent","Copper"],
    cols: ["1W","1M","3M","YTD","12M"],
    values: [
      [+1.1,+2.3,+4.5,+6.8,+14.2],
      [+1.8,+3.1,+6.0,+9.4,+22.1],
      [+0.4,+1.6,+3.2,+5.1,+10.4],
      [-0.6,+0.8,+2.4,+4.0,+11.3],
      [-1.2,-2.1,+1.8,+3.6,+8.7],
      [-0.3,-0.6,-1.2,-2.4,-4.1],
      [-0.2,-0.4,-0.9,-1.7,-2.8],
      [+0.6,+1.0,+2.1,+3.8,+9.2],
      [+0.3,+0.8,+1.6,+2.4,+4.1],
      [+1.4,+3.2,+6.1,+11.2,+18.4],
      [-2.1,-3.6,+1.2,+4.5,-6.3],
      [+1.7,+2.4,+5.0,+7.8,+13.1],
    ],
  },

  // Bar chart — fiscal impulse by quarter
  fiscal: {
    labels: ["Q1'25","Q2'25","Q3'25","Q4'25","Q1'26","Q2'26","Q3'26","Q4'26","Q1'27","Q2'27"],
    data:   [+0.4, +0.3, +0.1, -0.1, -0.0, +0.1, -0.2, -0.5, -0.6, -0.4],
    accent: [7,8],
  },

  // Catalysts (timeline)
  catalysts: [
    { date: "06 Jun", label: "ECB",        accent: false },
    { date: "12 Jun", label: "US CPI",     accent: true  },
    { date: "18 Jun", label: "FOMC",       accent: true  },
    { date: "27 Jun", label: "Core PCE",   accent: false },
    { date: "12 Jul", label: "Q2 GDP adv", accent: false },
    { date: "30 Jul", label: "FOMC",       accent: true  },
    { date: "22 Aug", label: "Jackson Hole", accent: true },
  ],

  // Risks
  risks: [
    { tag: "Inflation", title: "Sticky shelter & wages",
      body: "OER passthrough from new-lease repricing extends 2 quarters longer than house view. Adds ~25bps to terminal.",
      sev: 4 },
    { tag: "Fiscal",    title: "TCJA snap-back gridlock",
      body: "Failure to extend expiring provisions removes ~0.6pp from 2027 growth; magnifies cyclical earnings vulnerability.",
      sev: 5 },
    { tag: "Geo",       title: "Strait of Hormuz tail",
      body: "10% probability of 30-day disruption pulls Brent toward $110, re-igniting headline CPI through Q4.",
      sev: 3 },
    { tag: "Credit",    title: "HY refi wall, 2027",
      body: "$520bn HY refi calendar concentrated in H1 2027 at +180bps to coupon — tail risk for CCC names.",
      sev: 4 },
    { tag: "Policy",    title: "Election-cycle Fed pressure",
      body: "Verbal interventions during election season could de-anchor 5y5y inflation breakevens; we're long convexity here.",
      sev: 3 },
  ],

  // Recent data / filings (for macro = data prints)
  prints: [
    { date: "27 May", time: "08:30", label: "Durable Goods, Apr",   actual:"-0.3%", cons:"+0.1%", surprise:-1.2 },
    { date: "23 May", time: "10:00", label: "Existing Home Sales",  actual:"4.14M", cons:"4.20M", surprise:-0.4 },
    { date: "16 May", time: "08:30", label: "CPI, Apr (Core YoY)",  actual:"+3.4%", cons:"+3.6%", surprise:+0.8, accent:true },
    { date: "14 May", time: "14:00", label: "FOMC Minutes",         actual:"Hold",  cons:"Hold",  surprise:0,   accent:true },
    { date: "08 May", time: "08:30", label: "NFP, Apr",             actual:"175K",  cons:"243K",  surprise:-1.4, accent:true },
    { date: "30 Apr", time: "08:30", label: "ECI, Q1",              actual:"+1.2%", cons:"+1.0%", surprise:+0.6 },
  ],

  // Headline figures
  hero: [
    { k: "10Y UST",    v: "4.21%",   d: "-3.4bp",  spark: [4.32,4.28,4.34,4.31,4.29,4.24,4.22,4.21] },
    { k: "2Y UST",     v: "4.62%",   d: "-1.8bp",  spark: [4.70,4.66,4.68,4.64,4.65,4.62,4.61,4.62] },
    { k: "DXY",        v: "102.34",  d: "+0.12%",  spark: [101.8,102.1,102.0,102.3,102.4,102.2,102.3,102.34] },
    { k: "S&P 500",    v: "5,684",   d: "+0.41%",  spark: [5604,5620,5648,5631,5660,5655,5672,5684] },
    { k: "VIX",        v: "13.4",    d: "-0.6",    spark: [14.2,14.0,13.9,13.6,13.8,13.5,13.4,13.4] },
    { k: "Brent",      v: "$78.20",  d: "-1.10",   spark: [80.1,79.6,79.0,78.8,78.3,78.5,78.1,78.20] },
  ],
};

window.SAMPLE = SAMPLE;
