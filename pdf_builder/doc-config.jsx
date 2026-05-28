/* global window */

// Sample multi-page document. Replace with pipeline output later.
const uid = () => Math.random().toString(36).slice(2, 9);
const B = (type, span, props, rows) => ({
  id: uid(), type, span,
  ...(rows ? { rows } : {}),
  ...(props ? { props } : {}),
});

const INITIAL_DOC = {
  meta: {
    title:    "Late-Cycle Crosscurrents",
    subtitle: "H2 2026 Macro Outlook",
    edition:  "Macro Quarterly · Mid-Cycle Edition",
    date:     "27 May 2026",
  },
  pages: [
    // PAGE 1 — Cover (the original Variation A note, rendered in-place)
    {
      id: uid(),
      kind: "cover",
      eyebrow: "Macro Quarterly · H2 2026 Outlook",
    },

    // PAGE 2 — Scenarios
    {
      id: uid(),
      eyebrow: "§II — Scenario Analysis",
      blocks: [
        B("section",     12, { roman:"II", title:"Scenario Analysis",
                                lede:"We model three paths from end-Q2 2026. Probabilities sum to 100%; cross-asset response is keyed off the 10Y UST anchor." }),
        B("scenarios",    5),
        B("scenariofan",  7, { kicker:"II.a", title:"10Y UST · projected path", height: 200 }),
        B("cpi",          7),
        B("fiscal",       5),
      ],
    },

    // PAGE 3 — Catalysts & Data
    {
      id: uid(),
      eyebrow: "§III — Catalysts &amp; Tape",
      blocks: [
        B("section",   12, { roman:"III", title:"Catalysts & Recent Data",
                              lede:"The window between June CPI and Jackson Hole frames the next leg. We size positions to the volatility around these three prints." }),
        B("catalysts", 12),
        B("prints",     7),
        B("heatmap",    5, { rows: 8 }),
      ],
    },

    // PAGE 4 — Risks
    {
      id: uid(),
      eyebrow: "§IV — Risks",
      blocks: [
        B("section",   12, { roman:"IV", title:"Risks to House View",
                              lede:"Five tails ranked by impact × probability. Each is hedged in the model portfolio." }),
        B("risks",     12),
        B("pullquote", 12, { text:"Convexity over conviction. Hedge cheaply, size to your tail, and stop fighting the last war." }),
        B("authors",   12),
      ],
    },

    // PAGE 5 — Disclosures
    {
      id: uid(),
      eyebrow: "§V — Disclosures",
      blocks: [
        B("section",    12, { roman:"V", title:"Disclosures" }),
        B("disclosure", 12),
      ],
    },
  ],
};

window.INITIAL_DOC = INITIAL_DOC;
window.uid = uid;
