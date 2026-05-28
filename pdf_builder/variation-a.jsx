/* global React, Sparkline, Sparkbars, LineChart, ScenarioFan, BarChart, Heatmap, Timeline, SAMPLE */

// =========================================================
// VARIATION A — Classic Research Note (configurable)
// Tweaks-aware. Pass `tweaks` prop or omit for defaults.
// =========================================================

const DEFAULT_TWEAKS = {
  accent:    "#a23b1f",       // oxblood
  accentDeep:"#7d2a14",
  paper:     "#f4f0e6",       // cream
  paperDeep: "#ece6d4",
  rule:      "#c9bfae",
  ruleSoft:  "#ddd3c0",
  density:   "standard",      // "compact" | "standard" | "loose"
  masthead:  "classic",       // "classic" | "engraved" | "modern"
  showHero:  true,
  lower:     "risks-prints-fiscal", // | "risks-prints-heatmap" | "risks-heatmap-fiscal"
};

const DENSITY = {
  compact:  { pad:"22px 26px 20px", gap:10, rowGap:5, bodySize:11,   thesisSize:11,   headlineSize:34 },
  standard: { pad:"28px 32px 24px", gap:14, rowGap:6, bodySize:12.5, thesisSize:11.5, headlineSize:38 },
  loose:    { pad:"36px 42px 30px", gap:20, rowGap:8, bodySize:13,   thesisSize:12,   headlineSize:42 },
};

function MastheadClassic({ S }) {
  return (
    <div>
      <div className="eyebrow" style={{ marginBottom:4 }}>{S.firm} · {S.desk}</div>
      <div className="nameplate">Macro Quarterly</div>
      <div className="label" style={{ marginTop:3 }}>{S.city}</div>
    </div>
  );
}
function MastheadEngraved({ S }) {
  return (
    <div>
      <div className="eyebrow" style={{ marginBottom:4 }}>{S.firm} · {S.desk}</div>
      <div className="serif smallcaps" style={{
        fontWeight:700, fontSize:28, letterSpacing:"0.06em", lineHeight:1,
      }}>
        Macro Quarterly
      </div>
      <div className="label" style={{ marginTop:3 }}>{S.city}</div>
    </div>
  );
}
function MastheadModern({ S }) {
  return (
    <div>
      <div className="eyebrow" style={{ marginBottom:4, color:"var(--accent)" }}>{S.firm}</div>
      <div className="sans" style={{
        fontWeight:700, fontSize:28, letterSpacing:"-0.02em", lineHeight:1,
        color:"var(--ink)",
      }}>
        Macro / Quarterly
      </div>
      <div className="label" style={{ marginTop:3 }}>{S.desk} · {S.city}</div>
    </div>
  );
}

function VariationA({ tweaks: tIn }) {
  const S = SAMPLE;
  const t = { ...DEFAULT_TWEAKS, ...(tIn || {}) };
  const d = DENSITY[t.density] || DENSITY.standard;

  const Masthead = t.masthead === "engraved" ? MastheadEngraved
                 : t.masthead === "modern"   ? MastheadModern
                 :                              MastheadClassic;

  // CSS variable overrides scoped to this artboard
  const pageStyle = {
    padding: d.pad,
    display: "flex",
    flexDirection: "column",
    "--accent":      t.accent,
    "--accent-deep": t.accentDeep,
    "--paper":       t.paper,
    "--paper-deep":  t.paperDeep,
    "--rule":        t.rule,
    "--rule-soft":   t.ruleSoft,
    background:      t.paper,
  };

  // Which 3 lower sections to render
  const lowerCols = {
    "risks-prints-fiscal":  ["risks","prints","fiscal"],
    "risks-prints-heatmap": ["risks","prints","heatmap"],
    "risks-heatmap-fiscal": ["risks","heatmap","fiscal"],
  }[t.lower] || ["risks","prints","fiscal"];

  return (
    <div className="page" style={pageStyle}>

      {/* === Masthead === */}
      <header>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-end", gap:12 }}>
          <Masthead S={S} />
          <div style={{ textAlign:"right" }}>
            <div className="label" style={{ marginBottom:3 }}>{S.vol}</div>
            <div className="mono" style={{ fontSize:13, fontWeight:600 }}>{S.date}</div>
            <div className="stamp" style={{ marginTop:6 }}>Internal · Buy-Side Only</div>
          </div>
        </div>
        <hr className="rule-double" style={{ margin:"10px 0 6px" }} />
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", gap:8 }}>
          <div className="kicker">Mid-Cycle Edition · H2 2026 Outlook</div>
          <div className="label">Page 1 of 12 · Distribute Internally</div>
        </div>
        <hr className="rule" style={{ margin:"6px 0 14px" }} />
      </header>

      {/* === Title block === */}
      <div style={{ display:"grid", gridTemplateColumns:"1fr 220px", gap:20, marginBottom:14 }}>
        <div>
          <div className="kicker" style={{ marginBottom:6 }}>Thesis</div>
          <h1 className="h-display" style={{ fontSize: d.headlineSize }}>{S.title}</h1>
          <p style={{ fontFamily:"var(--serif)", fontStyle:"italic", fontSize:14.5,
                      lineHeight:1.35, color:"var(--ink-2)", margin:"8px 0 0",
                      maxWidth:"56ch" }}>
            {S.subtitle}
          </p>
        </div>
        <aside style={{ borderLeft:"1px solid var(--rule)", paddingLeft:14 }}>
          <div className="label label-accent" style={{ marginBottom:6 }}>Bottom Line</div>
          <p className="body-tight" style={{ color:"var(--ink)", fontSize:11.5, fontWeight:500, margin:0 }}>
            {S.bottomline}
          </p>
          <div style={{ display:"flex", gap:4, marginTop:10, flexWrap:"wrap" }}>
            <span className="tag accent">Duration: Add</span>
            <span className="tag">Equity: Trim</span>
            <span className="tag accent">Vol: Long</span>
          </div>
        </aside>
      </div>

      <hr className="rule-thick" style={{ marginBottom: t.showHero ? 12 : 14 }} />

      {/* === Hero key levels strip === */}
      {t.showHero && (
        <React.Fragment>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(6, 1fr)", gap:0, marginBottom:14 }}>
            {S.hero.map((m,i)=>(
              <div key={i} style={{
                padding:"6px 10px",
                borderRight: i<5 ? "1px solid var(--rule-soft)" : "none",
              }}>
                <div className="label" style={{ fontSize:8 }}>{m.k}</div>
                <div className="mono" style={{ fontSize:15, fontWeight:600, color:"var(--ink)", marginTop:2 }}>{m.v}</div>
                <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginTop:2 }}>
                  <span className="mono" style={{
                    fontSize:9.5,
                    color: m.d.startsWith("-") ? "var(--down)" : (m.d.startsWith("+") ? "var(--up)" : "var(--ink-3)")
                  }}>{m.d}</span>
                  <Sparkline data={m.spark} width={50} height={14} />
                </div>
              </div>
            ))}
          </div>
          <hr className="rule" style={{ marginBottom:14 }} />
        </React.Fragment>
      )}

      {/* === Two-column body === */}
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1px 1fr", gap:16, marginBottom:14 }}>
        {/* Left column — exec summary */}
        <section>
          <div className="kicker" style={{ marginBottom:6 }}>I. Executive Summary</div>
          <h2 className="h-section" style={{ marginBottom:6 }}>Four moves into the last mile</h2>
          <div className="body-tight dropcap" style={{ fontSize: d.bodySize }}>
            <p>
              The disinflation narrative that propelled risk through 2025 is entering its
              least telegenic phase. Headline CPI has cleared the easy gains; what remains
              is a slow grind through shelter and core services where the Fed has the least
              leverage. We move <em>Base from Bull</em> across asset allocations and tilt
              into convexity over conviction.
            </p>
            <p>
              Our four-point view follows. Each is sized to a specific catalyst window;
              all are paired with downside hedges that we believe trade cheap relative to
              realized cross-asset vol.
            </p>
          </div>

          <ol style={{ margin:"10px 0 0", paddingLeft:0, listStyle:"none" }}>
            {S.thesis.map((th,i)=>(
              <li key={i} style={{
                display:"grid", gridTemplateColumns:"22px 1fr", gap:6,
                padding:"7px 0",
                borderTop: i===0 ? "1px solid var(--rule)" : "1px solid var(--rule-soft)",
              }}>
                <span className="mono" style={{ fontSize:13, color:"var(--accent)", fontWeight:700 }}>
                  {String(i+1).padStart(2,"0")}
                </span>
                <span className="body-tight" style={{ fontSize:d.thesisSize, margin:0 }}>{th}</span>
              </li>
            ))}
          </ol>
        </section>

        <div className="vrule" />

        {/* Right column — scenarios table + fan */}
        <section>
          <div className="kicker" style={{ marginBottom:6 }}>II. Scenarios &amp; Estimates</div>
          <h2 className="h-section" style={{ marginBottom:8 }}>Three paths through year-end</h2>

          <table className="data" style={{ marginBottom:10 }}>
            <thead>
              <tr>
                <th></th>
                {S.scenarios.cols.map((c,i)=>(
                  <th key={i} className="n" style={{
                    color: i===0 ? "var(--down)" : (i===2 ? "var(--up)" : "var(--ink)"),
                  }}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {S.scenarios.rows.map((r,i)=>(
                <tr key={i} style={{ fontWeight: r.bold ? 700 : 400 }}>
                  <td className="name">{r.label}</td>
                  {r.vals.map((v,j)=>(
                    <td key={j} className="n" style={{
                      color: j===1 ? "var(--ink)" : "var(--ink-2)",
                      fontWeight: j===1 ? 600 : 400,
                    }}>{v}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>

          <div className="label" style={{ marginBottom:4 }}>10Y UST Path · Bear / Base / Bull</div>
          <ScenarioFan width={372} height={150}
            bear={S.proj.bear} base={S.proj.base} bull={S.proj.bull}
            xLabels={S.proj.xLabels} pivot={0} />
          <div className="label" style={{ fontSize:8, marginTop:4, color:"var(--ink-4)" }}>
            Source: H&amp;R Strategy. Dashed lines indicate tail scenarios at ±1σ from base.
          </div>
        </section>
      </div>

      <hr className="rule" style={{ marginBottom:14 }} />

      {/* === Catalysts timeline === */}
      <section style={{ marginBottom:14 }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"baseline" }}>
          <div>
            <div className="kicker">III. Catalysts</div>
            <h2 className="h-section" style={{ margin:"2px 0 0" }}>Calendar through Jackson Hole</h2>
          </div>
          <div className="label">Jun 06 — Aug 22 · 2026</div>
        </div>
        <div style={{ marginTop:6 }}>
          <Timeline events={S.catalysts} width={816} height={68} />
        </div>
      </section>

      <hr className="rule" style={{ marginBottom:14 }} />

      {/* === Lower row: 3 sections, configurable === */}
      <div style={{
        display:"grid",
        gridTemplateColumns:"1.1fr 1px 1fr 1px 1fr",
        gap:14, flex:1,
      }}>
        {lowerCols.map((sec, idx) => (
          <React.Fragment key={sec}>
            {idx > 0 && <div className="vrule-soft" />}
            {sec === "risks" && (
              <section>
                <div className="kicker" style={{ marginBottom:6 }}>IV. Risks</div>
                <h2 className="h-sub" style={{ marginBottom:8 }}>Five tail concerns, ranked</h2>
                {S.risks.map((r,i)=>(
                  <div key={i} style={{
                    padding:"6px 0",
                    borderTop: i===0 ? "1px solid var(--rule)" : "1px solid var(--rule-soft)"
                  }}>
                    <div style={{ display:"flex", justifyContent:"space-between", alignItems:"baseline", marginBottom:2 }}>
                      <span className="label label-accent">{r.tag}</span>
                      <span className="mono" style={{ fontSize:9, color:"var(--ink-3)" }}>
                        {"●".repeat(r.sev)}{"○".repeat(5-r.sev)}
                      </span>
                    </div>
                    <div className="h-sub" style={{ fontSize:11.5, marginBottom:2 }}>{r.title}</div>
                    <div className="body-tight" style={{ fontSize:10.5, color:"var(--ink-2)" }}>{r.body}</div>
                  </div>
                ))}
              </section>
            )}
            {sec === "prints" && (
              <section>
                <div className="kicker" style={{ marginBottom:6 }}>V. Recent Prints</div>
                <h2 className="h-sub" style={{ marginBottom:8 }}>Macro tape, last 30 days</h2>
                <table className="data">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Release</th>
                      <th className="n">Act.</th>
                      <th className="n">Cons.</th>
                      <th className="n">σ</th>
                    </tr>
                  </thead>
                  <tbody>
                    {S.prints.map((p,i)=>(
                      <tr key={i} style={{ fontWeight: p.accent ? 600 : 400 }}>
                        <td className="mono" style={{ fontSize:9.5 }}>{p.date}</td>
                        <td className="name" style={{ fontSize:10 }}>{p.label}</td>
                        <td className="n">{p.actual}</td>
                        <td className="n" style={{ color:"var(--ink-3)" }}>{p.cons}</td>
                        <td className="n" style={{
                          color: p.surprise>0.5 ? "var(--up)" : (p.surprise<-0.5 ? "var(--down)" : "var(--ink-3)")
                        }}>{p.surprise>0?"+":""}{p.surprise.toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            )}
            {sec === "fiscal" && (
              <section>
                <div className="kicker" style={{ marginBottom:6 }}>VI. Fiscal Impulse</div>
                <h2 className="h-sub" style={{ marginBottom:8 }}>Pivot to drag, Q3 2026</h2>
                <BarChart width={252} height={130}
                  data={S.fiscal.data} labels={S.fiscal.labels}
                  accentIdx={S.fiscal.accent} />
                <div className="body-tight" style={{ fontSize:10.5, marginTop:6, color:"var(--ink-2)" }}>
                  Contribution to YoY GDP, pp. TCJA expirations bind Q4 2026, removing
                  <span className="num" style={{ color:"var(--accent)" }}> 0.6pp </span>
                  from 2027 — the largest fiscal drag of the cycle.
                </div>
              </section>
            )}
            {sec === "heatmap" && (
              <section>
                <div className="kicker" style={{ marginBottom:6 }}>VI. Cross-Asset</div>
                <h2 className="h-sub" style={{ marginBottom:8 }}>Returns recap, %</h2>
                <Heatmap rows={S.heatmap.rows.slice(0,8)}
                         cols={S.heatmap.cols}
                         values={S.heatmap.values.slice(0,8)}
                         width={252} height={180} />
              </section>
            )}
          </React.Fragment>
        ))}
      </div>

      {/* === Footer === */}
      <footer style={{ marginTop:14 }}>
        <hr className="rule-thick" style={{ marginBottom:6 }} />
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
          <div className="foot">
            {S.authors.map(a => a.name).join(" · ")}
          </div>
          <div className="foot">
            See disclosures, p. 12 · © 2026 {S.firm}
          </div>
        </div>
      </footer>
    </div>
  );
}

window.VariationA = VariationA;
window.DEFAULT_TWEAKS = DEFAULT_TWEAKS;
